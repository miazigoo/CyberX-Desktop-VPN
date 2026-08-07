#!/bin/bash
# Запуск CyberX VPN из исходников.
cd "$(dirname "$(readlink -f "$0")")" || exit 1
exec .venv/bin/python main.py "$@"
