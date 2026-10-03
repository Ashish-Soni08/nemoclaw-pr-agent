#!/usr/bin/env bash
# Step 2: register the GitHub and Firecrawl keys with the OpenShell gateway and attach them
# to the sandbox. The sandbox only sees placeholders; the gateway injects the real values
# at egress, for the hosts and binaries named in policies/provider-profiles/.
# Usage: GITHUB_TOKEN=... FIRECRAWL_API_KEY=... scripts/setup-credentials.sh
source "$(dirname "$0")/_lib.sh"
need openshell "installed with NemoClaw"
need_env GITHUB_TOKEN "classic token with public_repo scope for the agent's GitHub account"
need_env FIRECRAWL_API_KEY "Firecrawl API key"

register() {  # profile-file provider-name profile-id env-name value
  local file="$1" name="$2" id="$3" env="$4" value="$5"
  # First run imports the profile. Later runs update it in place: import refuses existing
  # ids, and update needs the stored resource_version, which we copy from an export.
  if ! openshell provider profile import --file "$file" 2>/dev/null; then
    local rv tmp
    rv="$(openshell provider profile export "$id" | sed -n 's/^[[:space:]]*"*resource_version"*:[[:space:]]*["'\'']*\([0-9][0-9]*\).*/\1/p' | head -1)"
    [[ -n "$rv" ]] || { echo "could not read resource_version of $id from: openshell provider profile export $id" >&2; exit 1; }
    tmp="$(mktemp --suffix=.yaml)"
    { grep -v '^resource_version:' "$file"; echo "resource_version: $rv"; } > "$tmp"
    openshell provider profile update --file "$tmp" "$id"
    rm -f "$tmp"
  fi
  if openshell provider list 2>/dev/null | grep -qw "$name"; then
    env "$env=$value" openshell provider update "$name" --credential "$env"
  else
    env "$env=$value" openshell provider create --name "$name" --type "$id" --credential "$env"
  fi
  openshell sandbox provider attach "$SANDBOX" "$name" || echo "(already attached)"
}

say "GitHub (api.github.com, injected into PRAGENT_GITHUB_TOKEN)"
register "$REPO_DIR/policies/provider-profiles/pr-agent-github.yaml" pr-agent-github pr-agent-github-v1 PRAGENT_GITHUB_TOKEN "$GITHUB_TOKEN"
say "Firecrawl (api.firecrawl.dev, injected into PRAGENT_FIRECRAWL_KEY)"
register "$REPO_DIR/policies/provider-profiles/pr-agent-firecrawl.yaml" pr-agent-firecrawl pr-agent-firecrawl-v1 PRAGENT_FIRECRAWL_KEY "$FIRECRAWL_API_KEY"

openshell sandbox provider list "$SANDBOX"
save_provider_placeholders
say "Next: scripts/deploy.sh"
