#!/usr/bin/env bash
set -euo pipefail
repo="${REPO:-$(gh repo view --json nameWithOwner --jq .nameWithOwner)}"
cmd="${1:-status}"
current() { gh api "/repos/${repo}" --jq .allow_auto_merge; }
case "${cmd}" in
  on)  gh api -X PATCH "/repos/${repo}" -F allow_auto_merge=true  >/dev/null; echo "auto-merge: ON  (${repo})";;
  off) gh api -X PATCH "/repos/${repo}" -F allow_auto_merge=false >/dev/null; echo "auto-merge: OFF (${repo})";;
  status) [ "$(current)" = true ] && echo "auto-merge: ON  (${repo})" || echo "auto-merge: OFF (${repo})";;
  *) echo "usage:  {on|off|status}" >&2; exit 2;;
esac
