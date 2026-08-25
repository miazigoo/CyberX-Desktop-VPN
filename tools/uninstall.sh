#!/bin/bash
# Удаление sudoers-правила CyberX VPN (файлы приложения не трогаем).
set -euo pipefail

SUDOERS="/etc/sudoers.d/cyberx-vpn"

if [ -f "$SUDOERS" ]; then
    sudo rm -f "$SUDOERS"
    echo "удалено: $SUDOERS"
else
    echo "sudoers-правило не найдено: $SUDOERS"
fi
