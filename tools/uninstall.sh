#!/bin/bash
# Удаляет системную часть и ярлык. Пользовательская папка с настройками сохраняется.
set -euo pipefail
system_dir=/usr/local/lib/cyberx-vpn
data_dir="${XDG_DATA_HOME:-$HOME/.local/share}"
if ip link show cyberx0 >/dev/null 2>&1; then
    echo "Сначала отключите CyberX VPN и закройте приложение." >&2
    exit 1
fi
sudo rm -f "$system_dir/helper.sh" "$system_dir/sing-box" /etc/sudoers.d/cyberx-vpn
if [[ -d $system_dir ]]; then sudo rmdir "$system_dir"; fi
rm -f "$data_dir/applications/cyberx-vpn.desktop" "$data_dir/icons/hicolor/256x256/apps/cyberx-vpn.png"
echo "Системный помощник и ярлык удалены. Папка приложения и настройки сохранены."
