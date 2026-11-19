#!/bin/bash
# Движок для Linux amd64, с проверкой SHA-256 опубликованного архива.
set -euo pipefail
VERSION=1.11.15
SHA256=950af37eb2d7e55dddae34a18411cd617303fd99d2dc75bc76b6dd9fcd97d9c5
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
[[ $(uname -m) == x86_64 ]] || { echo "Требуется x86_64 (amd64)." >&2; exit 1; }

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
archive="sing-box-${VERSION}-linux-amd64"
url="https://github.com/SagerNet/sing-box/releases/download/v${VERSION}/$archive.tar.gz"
echo "Скачиваю $url"
curl -fLsS --retry 2 --max-time 300 -o "$tmp/archive.tar.gz" "$url"
(cd "$tmp" && echo "$SHA256  archive.tar.gz" | sha256sum --check --status) || {
    echo "Контрольная сумма sing-box не совпадает." >&2; exit 1;
}
tar -xzf "$tmp/archive.tar.gz" -C "$tmp" "$archive/sing-box"
install -m755 "$tmp/$archive/sing-box" "$ROOT/sing-box"
"$ROOT/sing-box" version
