#!/bin/bash
# Скачивает sing-box (pinned версия) с GitHub releases рядом с проектом.
# Бинарник не храним в git — он нужен только для запуска/сборки.
set -euo pipefail

VERSION="1.11.15"
DIR="$(dirname "$(readlink -f "$0")")/.."
OUT="$DIR/sing-box"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

URL="https://github.com/SagerNet/sing-box/releases/download/v${VERSION}/sing-box-${VERSION}-linux-amd64.tar.gz"
echo "Скачиваю $URL"
curl -sL --fail --max-time 300 -o "$TMP/sb.tar.gz" "$URL"
tar -xzf "$TMP/sb.tar.gz" -C "$TMP"
cp "$TMP/sing-box-${VERSION}-linux-amd64/sing-box" "$OUT"
chmod +x "$OUT"
"$OUT" version
