#!/bin/bash
# Одноразовая настройка прав (запускается от root через pkexec).
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: нужен root" >&2
    exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HELPER="$(readlink -f "$ROOT/helper.sh")"
INSTALL_DIR="${INSTALL_DIR:-$HOME/apps/cyberx-vpn}"
USER="${PKEXEC_UID:+$(id -nu "$PKEXEC_UID")}"
USER="${USER:-${SUDO_USER:-$(logname 2>/dev/null || whoami)}}"
SUDOERS="/etc/sudoers.d/cyberx-vpn"

[ -x "$HELPER" ] || { echo "ERROR: нет $HELPER" >&2; exit 1; }

tmp="$(mktemp)"
cat >"$tmp" <<EOF
# CyberX VPN — passwordless helper for $USER
$USER ALL=(root) NOPASSWD: $HELPER up
$USER ALL=(root) NOPASSWD: $HELPER down
$USER ALL=(root) NOPASSWD: $HELPER status
EOF

if [ -e "$INSTALL_DIR/helper.sh" ]; then
    apps_helper="$(readlink -f "$INSTALL_DIR/helper.sh")"
    if [ "$apps_helper" != "$HELPER" ]; then
        cat >>"$tmp" <<EOF
$USER ALL=(root) NOPASSWD: $INSTALL_DIR/helper.sh up
$USER ALL=(root) NOPASSWD: $INSTALL_DIR/helper.sh down
$USER ALL=(root) NOPASSWD: $INSTALL_DIR/helper.sh status
EOF
    fi
fi

install -m440 "$tmp" "$SUDOERS"
rm -f "$tmp"
visudo -cf "$SUDOERS"

chown root:root "$HELPER" "$ROOT/sing-box"
chmod 755 "$HELPER" "$ROOT/sing-box"

echo "OK: passwordless sudo для CyberX VPN настроен"
