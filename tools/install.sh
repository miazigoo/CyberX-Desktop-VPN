#!/bin/bash
# Установка пользовательского приложения и системного помощника TUN.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INSTALL_DIR="${INSTALL_DIR:-$HOME/apps/cyberx-vpn}"
mode=bundle

usage() {
    cat <<HELP
Использование: $0 [--dir PATH] [--dev | --skip-build]
  --dir PATH     каталог приложения (по умолчанию ~/apps/cyberx-vpn)
  --dev          запускать GUI из этого клона через run.sh
  --skip-build   установить готовый dist/cyberx-vpn
HELP
}

while (($#)); do
    case "$1" in
        --dir) INSTALL_DIR="${2:?Укажите каталог после --dir}"; shift 2 ;;
        --dev) mode=dev; shift ;;
        --skip-build) mode=dist; shift ;;
        -h|--help) usage; exit 0 ;;
        *) usage >&2; exit 1 ;;
    esac
done

die() { echo "Ошибка: $*" >&2; exit 1; }
[[ $(id -u) != 0 ]] || die "Запустите установщик от своего пользователя, без sudo."
[[ $(uname -m) == x86_64 ]] || die "Для этой сборки требуется Ubuntu/Debian x86_64 (amd64)."
for tool in python3 ip pkexec sudo; do
    command -v "$tool" >/dev/null || die "Не найдена команда $tool. Установите пакеты из README."
done
if ip link show cyberx0 >/dev/null 2>&1; then
    die "Отключите действующий VPN CyberX и повторите установку."
fi

INSTALL_DIR="$(realpath -m -- "$INSTALL_DIR")"
cd "$ROOT"
if [[ $mode != dist ]]; then
    python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' || die "Нужен Python 3.10 или новее."
    if [[ ! -x .venv/bin/python ]]; then
        python3 -m venv .venv || die "Установите python3-venv и повторите запуск."
    fi
    if [[ $mode == dev ]]; then
        .venv/bin/python -m pip install -e .
    else
        .venv/bin/python -m pip install -e '.[bundle]'
    fi
    [[ -x sing-box ]] || ./tools/fetch_singbox.sh
fi

if [[ $mode == bundle ]]; then
    .venv/bin/python -m PyInstaller --noconfirm cyberx-vpn.spec
fi

if [[ $mode == dev ]]; then
    engine="$ROOT/sing-box"
    launcher="$ROOT/run.sh"
else
    dist="$ROOT/dist/cyberx-vpn"
    [[ -x "$dist/cyberx-vpn" && -f "$dist/_internal/sing-box" ]] || die "Бандл в dist/cyberx-vpn не собран."
    case "$INSTALL_DIR/" in
        "$ROOT/"|"$dist/"*) die "Укажите отдельный каталог для установки приложения." ;;
    esac
    mkdir -p "$INSTALL_DIR"
    [[ -w "$INSTALL_DIR" ]] || die "Нет прав на запись в $INSTALL_DIR."
    engine="$dist/_internal/sing-box"
    launcher="$INSTALL_DIR/cyberx-vpn"
fi

"$ROOT/tools/setup-privileges.sh" "$engine"
if [[ $mode != dev ]]; then
    # Копируем только файлы приложения. Настройки и другие файлы пользователя сохраняются.
    cp -a -- "$dist/cyberx-vpn" "$dist/_internal" "$INSTALL_DIR/"
    mkdir -p "$INSTALL_DIR/assets"
    cp -a -- "$dist/_internal/assets/." "$INSTALL_DIR/assets/"
fi

data_dir="${XDG_DATA_HOME:-$HOME/.local/share}"
apps="$data_dir/applications"
icons="$data_dir/icons/hicolor/256x256/apps"
mkdir -p "$apps" "$icons"
install -m644 assets/cyberx_mark_256.png "$icons/cyberx-vpn.png"
python3 - "$launcher" "$apps/cyberx-vpn.desktop" <<'PY'
from pathlib import Path
import sys

launcher, target = sys.argv[1:]
# Exec has its own quoting rules on top of desktop-entry string escaping.
for char in ('\\', '"', '`', '$'):
    launcher = launcher.replace(char, '\\' + char)
launcher = launcher.replace('\\', '\\\\').replace('%', '%%')
template = Path('CyberXVPN.desktop').read_text()
Path(target).write_text(template.replace('__EXEC__', f'"{launcher}"'))
PY
echo "Готово. Откройте CyberX VPN в меню приложений или запустите: $launcher"
