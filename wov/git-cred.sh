#!/bin/sh
# git credential helper: reads GITHUB_TOKEN from site/secrets.env (never stored in git config or printed)
[ "$1" = get ] || exit 0
t=$(grep '^GITHUB_TOKEN=' /opt/wow/headless-dm/site/secrets.env | cut -d= -f2-)
echo username=x-access-token
echo "password=$t"
