#!/bin/bash
# wov: local patches on third-party submodules we do not fork (applied to the working tree before a build).
# Idempotent: a patch that is already applied is skipped.
cd "$(dirname "$0")/.." || exit 1
rc=0
for dir in wov/patches/*/; do
  mod=$(basename "$dir")
  for p in "$dir"*.patch; do
    [ -e "$p" ] || continue
    if git -c safe.directory='*' -C "src/modules/$mod" apply --reverse --check "$OLDPWD/$p" 2>/dev/null || git -c safe.directory='*' -C "src/modules/$mod" apply --reverse --check "$(pwd)/$p" 2>/dev/null; then
      echo "already applied: $mod/$(basename "$p")"
    elif git -c safe.directory='*' -C "src/modules/$mod" apply "$(pwd)/$p"; then
      echo "applied: $mod/$(basename "$p")"
    else
      echo "FAILED: $mod/$(basename "$p")"; rc=1
    fi
  done
done
exit $rc
