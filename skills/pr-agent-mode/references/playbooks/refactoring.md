### Refactoring

Adapted from poteto-mode `playbooks/refactoring.md` (cursor/plugins pstack, MIT). Only for issues that explicitly ask for the restructure. Never refactor on your own initiative.

**You own the contract. The structure changes, the behavior does not.**

1. **Pin the behavior first.** Run the repo's tests for the area; if coverage is thin, write a characterization test that captures current behavior before moving anything. Type checks and lint are not a pin.
2. **Name the missing structure** (**principle-laziness-protocol**). The reshape must delete branches or invalid states, not add indirection.
3. **Name the target shape** the issue asks for: module layout, names, call graph.
4. **Subtract before you add.** Delete dead code and one-caller wrappers first.
5. **Move in small behavior-preserving steps**, each keeping the pin green. Migrate every caller in the same diff; no compatibility shims unless the maintainer asked for a deprecation path. Grep for every renamed symbol, including strings and docs.
6. **Prove behavior is unchanged** on the real artifact (**principle-prove-it-works**): pin green, full suite matches baseline.
7. If the diff doesn't lower reader load, revert it and skip the issue with that reason.
8. Hand back for **self-review-gate**, then **Opening a PR**.

**Report:** what changed in structure, the pin, the equivalence proof, what was reverted.
