#!/bin/bash
# Устанавливает фиксированные исполняемые файлы для запуска через polkit.
set -euo pipefail
root_dir="$(cd "$(dirname "$0")/.." && pwd)"
system_dir=/usr/local/lib/cyberx-vpn
engine="${1:-$root_dir/sing-box}"
[[ -f "$engine" ]] || { echo "Не найден sing-box: $engine" >&2; exit 1; }

if ip link show cyberx0 >/dev/null 2>&1; then
    echo "Отключите CyberX VPN перед обновлением системного помощника." >&2
    exit 1
fi

echo "Для установки помощника в $system_dir нужен sudo."
sudo install -d -o root -g root -m755 "$system_dir"
sudo install -o root -g root -m755 "$engine" "$system_dir/sing-box"
sudo install -o root -g root -m755 "$root_dir/helper.sh" "$system_dir/helper.sh"
# Ранее это правило разрешало запуск скрипта из домашнего каталога от root.
sudo rm -f /etc/sudoers.d/cyberx-vpn
