# Configure GitHub repository protections using gh CLI
# Usage:
#   .\scripts\configure_github.ps1 -Owner "ORG" -Repo "REPO" -Branch "main"

param(
    [Parameter(Mandatory = $true)][string]$Owner,
    [Parameter(Mandatory = $true)][string]$Repo,
    [Parameter(Mandatory = $true)][string]$Branch
)

# Requires: GitHub CLI (`gh`) authenticated with sufficient permissions

$repo = "$Owner/$Repo"

# Enable auto-merge (rebase)
& gh api repos/$repo -X PATCH -f allow_auto_merge=true -f allow_rebase_merge=true

# Branch protection: require ai_suitability check
& gh api repos/$repo/branches/$Branch/protection -X PUT --input - <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["ai_suitability"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 1
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
