"""Run other people's code (installs, tests, repro scripts) where it can't reach the agent.

The NemoClaw sandbox runs everything as one user, so file permissions can't separate the
agent from the repo code it tests. Landlock can: it is an unprivileged Linux security
module, nestable inside OpenShell's own Landlock policy, and a process can only ever
narrow it. Code running under it

- can write only its workspace, the package caches and /tmp;
- can read the system (/usr, /etc, /opt, /proc, ...) but nothing else under the sandbox
  home: not pr-agent's state, gate verdicts, workspace metadata, interpreter or code,
  not Hermes' config, and not any credential file kept there;
- can't execute the private interpreter that the GitHub and Firecrawl keys are injected
  for, because it can't even see it;
- can't read /proc/<pid>/environ or ptrace any process outside its own domain (Landlock
  blocks ptrace across domains), so the placeholders in the agent's environment stay out
  of reach too.

Isolation is required by default: if the kernel lacks Landlock, repo code doesn't run at
all. `PR_AGENT_TEST_ISOLATION=off` turns it off; `pr-agent selfcheck` proves it works.
"""

from __future__ import annotations

import ctypes
import os
from collections.abc import Callable, Iterable
from pathlib import Path

# Syscall numbers are the same on x86_64 and aarch64 (generic table).
SYS_CREATE_RULESET, SYS_ADD_RULE, SYS_RESTRICT_SELF = 444, 445, 446
CREATE_RULESET_VERSION = 1
RULE_PATH_BENEATH = 1
PR_SET_NO_NEW_PRIVS = 38

EXECUTE, WRITE_FILE, READ_FILE, READ_DIR = 1 << 0, 1 << 1, 1 << 2, 1 << 3
REMOVE_DIR, REMOVE_FILE, MAKE_CHAR, MAKE_DIR = 1 << 4, 1 << 5, 1 << 6, 1 << 7
MAKE_REG, MAKE_SOCK, MAKE_FIFO, MAKE_BLOCK, MAKE_SYM = 1 << 8, 1 << 9, 1 << 10, 1 << 11, 1 << 12
REFER, TRUNCATE, IOCTL_DEV = 1 << 13, 1 << 14, 1 << 15

READ = EXECUTE | READ_FILE | READ_DIR
WRITE = WRITE_FILE | REMOVE_DIR | REMOVE_FILE | MAKE_DIR | MAKE_REG | MAKE_SOCK | MAKE_FIFO | MAKE_SYM

# Read-only system trees. Everything not listed (the sandbox home above all) is invisible.
SYSTEM_READ = ["/usr", "/bin", "/sbin", "/lib", "/lib32", "/lib64", "/libx32", "/etc", "/opt", "/proc", "/sys", "/run/systemd/resolve", "/var/lib"]
# Writable everywhere for every tool: scratch space and devices (/dev/null, /dev/tty, ...).
SHARED_WRITE = ["/tmp", "/var/tmp", "/dev"]
# Package caches under HOME. npx keeps pnpm and bun in ~/.npm/_npx, where the egress policy
# expects them, so HOME itself stays put and only these subtrees open up.
HOME_CACHES = [".cache", ".npm", ".yarn", ".bun", ".local/share/pnpm", ".pnpm-store", ".node-gyp"]


class IsolationUnavailable(RuntimeError):
    """The kernel can't sandbox repo code, and isolation is required."""


class _RulesetAttr(ctypes.Structure):
    _fields_ = [("handled_access_fs", ctypes.c_uint64)]


class _PathBeneathAttr(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("allowed_access", ctypes.c_uint64), ("parent_fd", ctypes.c_int32)]


def _libc() -> ctypes.CDLL:
    return ctypes.CDLL(None, use_errno=True)


def abi() -> int:
    """Landlock ABI version, or 0 when the kernel doesn't offer it."""
    try:
        v = _libc().syscall(SYS_CREATE_RULESET, None, ctypes.c_size_t(0), ctypes.c_uint32(CREATE_RULESET_VERSION))
    except (OSError, AttributeError):
        return 0
    return max(v, 0)


def required() -> bool:
    return os.environ.get("PR_AGENT_TEST_ISOLATION", "required").strip().lower() not in ("off", "0", "false", "no")


def _handled(version: int) -> int:
    mask = READ | WRITE | MAKE_CHAR | MAKE_BLOCK
    if version >= 2:
        mask |= REFER
    if version >= 3:
        mask |= TRUNCATE
    if version >= 5:
        mask |= IOCTL_DEV
    return mask


def restrict(write: Iterable[str | Path], read: Iterable[str | Path] = ()) -> None:
    """Narrow the calling process (and everything it starts) to these paths. Irreversible."""
    version = abi()
    if version < 1:
        raise IsolationUnavailable("this kernel has no Landlock; repo code can't be isolated")
    libc = _libc()
    handled = _handled(version)
    attr = _RulesetAttr(handled)
    fd = libc.syscall(SYS_CREATE_RULESET, ctypes.byref(attr), ctypes.c_size_t(ctypes.sizeof(attr)), ctypes.c_uint32(0))
    if fd < 0:
        raise IsolationUnavailable(f"landlock_create_ruleset failed: {os.strerror(ctypes.get_errno())}")
    try:
        file_bits = EXECUTE | READ_FILE | WRITE_FILE | (TRUNCATE if version >= 3 else 0) | (IOCTL_DEV if version >= 5 else 0)
        for paths, access in ((read, READ), (write, handled & ~(MAKE_CHAR | MAKE_BLOCK))):
            for p in paths:
                try:
                    pfd = os.open(str(p), os.O_PATH | os.O_CLOEXEC)
                except OSError:
                    continue  # paths that don't exist on this system are simply not granted
                try:
                    allowed = access if os.path.isdir(str(p)) else access & file_bits
                    rule = _PathBeneathAttr(allowed, pfd)
                    if libc.syscall(SYS_ADD_RULE, fd, RULE_PATH_BENEATH, ctypes.byref(rule), ctypes.c_uint32(0)) < 0:
                        raise IsolationUnavailable(f"landlock_add_rule({p}) failed: {os.strerror(ctypes.get_errno())}")
                finally:
                    os.close(pfd)
        if libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
            raise IsolationUnavailable(f"prctl(NO_NEW_PRIVS) failed: {os.strerror(ctypes.get_errno())}")
        if libc.syscall(SYS_RESTRICT_SELF, fd, ctypes.c_uint32(0)) < 0:
            raise IsolationUnavailable(f"landlock_restrict_self failed: {os.strerror(ctypes.get_errno())}")
    finally:
        os.close(fd)


# Toolchains repo code needs, wherever they're installed (a Node under ~/.nvm, say).
TOOLS = ["python3", "node", "npm", "npx", "yarn", "corepack", "git"]
# CA bundles for the egress proxy, which may live outside the system trees.
CA_VARS = ["SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "NODE_EXTRA_CA_CERTS", "PIP_CERT", "CURL_CA_BUNDLE"]


def _toolchain_roots(home: Path) -> list[str]:
    """Install prefixes of the tools on PATH, minus anything that would expose the agent."""
    import shutil

    private = [Path(os.environ.get("PR_AGENT_HOME", home / ".pr-agent")), home / ".hermes", Path("/sandbox/.pr-agent"), Path("/sandbox/.hermes")]
    roots = []
    for tool in TOOLS:
        found = shutil.which(tool)
        if not found:
            continue
        root = Path(os.path.realpath(found)).parent.parent  # .../bin/node -> the install prefix
        # Never the home directory itself, an ancestor of it, or the agent's own trees.
        if home.is_relative_to(root) or any(p.is_relative_to(root) or root.is_relative_to(p) for p in private):
            continue
        roots.append(str(root))
    return roots


def allowed_paths(workspace: Path, extra_write: Iterable[str | Path] = ()) -> tuple[list[str], list[str]]:
    home = Path(os.environ.get("HOME", str(Path.home())))
    write = [str(workspace), *SHARED_WRITE, *(str(home / c) for c in HOME_CACHES), *map(str, extra_write)]
    cas = sorted({os.environ[v] for v in CA_VARS if os.environ.get(v)})
    return write, [*SYSTEM_READ, *_toolchain_roots(home), *cas]


def preexec(workspace: Path, extra_write: Iterable[str | Path] = ()) -> Callable[[], None] | None:
    """A subprocess preexec_fn that jails the child, or None when isolation is switched off.

    Checked up front, in the parent, so a missing Landlock is a clear error rather than a
    child that dies before exec."""
    if not required():
        return None
    if abi() < 1:
        raise IsolationUnavailable("this kernel has no Landlock, so repo code can't be isolated; "
                                   "set PR_AGENT_TEST_ISOLATION=off only if you accept running it unsandboxed")
    home = Path(os.environ.get("HOME", str(Path.home())))
    for cache in HOME_CACHES:
        try:
            (home / cache).mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
    write, read = allowed_paths(workspace, extra_write)

    def _jail() -> None:
        restrict(write, read)

    return _jail
