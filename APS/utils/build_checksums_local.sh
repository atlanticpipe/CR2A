#!/usr/bin/env bash
# Rebuild/normalize arrays, refresh per-file size+sha, mirror arrays, and stamp top-level hash.
set -euo pipefail

MAN=contract-analysis-policy-bundle/policy/checksums_manifest_v1.json

# 0) Parse sanity + show what we start with
jq -e . "$MAN" >/dev/null
echo "START ->" \
  "$(jq -r '"artifacts=\(.artifacts|length // 0) canonical=\(.canonical|length // 0)"' "$MAN")"

# 1) Normalize arrays (avoid 'iterate over null')
tmp=$(mktemp)
jq '
  .artifacts = (.artifacts // .canonical // []) |
  .canonical = (.canonical // .artifacts // [])
' "$MAN" > "$tmp" && mv "$tmp" "$MAN"

# 2) Update component size_bytes/sha256 for whichever array exists
tmp=$(mktemp)
jq -c '(.canonical // .artifacts // [])[]' "$MAN" | while read -r ART; do
  p=$(jq -r '.path' <<<"$ART")
  [ -f "$p" ] || { echo "Missing file: $p" >&2; exit 1; }
  sz=$(stat -c%s "$p")
  sha=$(sha256sum "$p" | cut -d' ' -f1)

  jq --arg p "$p" --argjson sz "$sz" --arg sha "$sha" '
    ( .canonical |= ( ( . // [] )
        | map( if .path == $p then (.size_bytes = $sz | .sha256 = $sha) else . end ) ) ) |
    ( .artifacts |= ( ( . // [] )
        | map( if .path == $p then (.size_bytes = $sz | .sha256 = $sha) else . end ) ) )
  ' "$MAN" > "$tmp" && mv "$tmp" "$MAN"
done

# 3) Mirror + sort + stamp top-level manifest_sha256 (uses artifacts[] like Policy Validate)
CALC=$(
  jq -S '.artifacts = ((.artifacts // .canonical // []) | sort_by(.path))
         | del(.manifest_sha256)' "$MAN" | sha256sum | cut -d' ' -f1
)
jq --arg h "$CALC" '
  .artifacts = ((.artifacts // .canonical // []) | sort_by(.path)) |
  .canonical = ((.canonical // .artifacts // []) | sort_by(.path)) |
  .manifest_sha256 = $h
' "$MAN" > "$MAN.tmp" && mv "$MAN.tmp" "$MAN"

# 4) Show result
jq -r '. as $r |
       "DONE  -> artifacts=\($r.artifacts|length) canonical=\($r.canonical|length) hash=\($r.manifest_sha256)"' "$MAN"
