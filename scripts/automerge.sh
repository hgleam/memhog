#!/usr/bin/env bash
set -euo pipefail
repo="${REPO:-$(gh repo view --json nameWithOwner --jq .nameWithOwner)}"
cmd="${1:-status}"
auto()  { gh api "/repos/${repo}" --jq .allow_auto_merge; }
prune() { gh api "/repos/${repo}" --jq .delete_branch_on_merge; }
case "${cmd}" in
  # delete_branch_on_merge も立てる。GITHUB_TOKEN 起点の自動マージでは発火しないが
  # (cascade 抑制)、手動マージ・PAT 運用では効くので合わせて ON にしておく。
  on)  gh api -X PATCH "/repos/${repo}" -F allow_auto_merge=true -F delete_branch_on_merge=true >/dev/null
       echo "auto-merge: ON  / branch-delete: ON  (${repo})";;
  off) gh api -X PATCH "/repos/${repo}" -F allow_auto_merge=false >/dev/null
       echo "auto-merge: OFF (${repo})";;
  status) echo "auto-merge: $([ "$(auto)" = true ] && echo ON || echo OFF)  / branch-delete: $([ "$(prune)" = true ] && echo ON || echo OFF)  (${repo})";;
  *) echo "usage: $0 {on|off|status}" >&2; exit 2;;
esac
