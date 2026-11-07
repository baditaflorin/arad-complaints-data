#!/usr/bin/env bash
# Create/push this PUBLIC repository; publish its public data site only with --pages.
set -euo pipefail
cd "$(dirname "$0")/.."
repo_name="$(basename "$PWD")"
owner="$(gh api user --jq .login)"
target="$owner/$repo_name"
if gh repo view "$target" --json isPrivate --jq .isPrivate >/dev/null 2>&1; then
  if [[ "$(gh repo view "$target" --json isPrivate --jq .isPrivate)" != "false" ]]; then
    printf 'Existing repository is private; set its visibility deliberately before publishing: %s\n' "$target" >&2
    exit 1
  fi
else
  gh repo create "$target" --public --description 'Arad civic data: reproducible source, CSV, JSON, GeoJSON and download portal'
fi
if [[ ! -d .git ]]; then git init -b main; fi
git add .
if ! git diff --cached --quiet; then git commit -m 'Add reproducible Arad data snapshot and download portal'; fi
if git remote get-url origin >/dev/null 2>&1; then
  if [[ "$(git remote get-url origin)" != "https://github.com/$target.git" ]]; then
    printf 'Unexpected origin; inspect before pushing.\n' >&2; exit 1
  fi
else
  git remote add origin "https://github.com/$target.git"
fi
git push -u origin main
if [[ "${1:-}" == "--pages" ]]; then
  pages_method=POST
  if gh api "repos/$target/pages" >/dev/null 2>&1; then pages_method=PUT; fi
  gh api --method "$pages_method" "repos/$target/pages" --input - <<'JSON'
{"build_type":"legacy","source":{"branch":"main","path":"/docs"}}
JSON
  printf 'Pages publication requested from main:/docs; verify: https://%s.github.io/%s/\n' "$owner" "$repo_name"
fi
