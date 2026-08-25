#!/bin/bash
# Установка CyberX VPN: копирование файлов и одноразовая настройка sudo.
# После установки connect/disconnect работают без повторного ввода пароля.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INSTALL_DIR="${INSTALL_DIR:-$HOME/apps/cyberx-vpn}"
SKIP_BUILD=0
DEV_MODE=0
SUDOERS_ONLY=0

usage() {
    cat <<EOF
Использование: $0 [опции]

  --dir PATH        каталог установки (по умолчанию: ~/apps/cyberx-vpn)
  --dev             установить из исходников (без PyInstaller)
  --skip-build      не собирать бандл, использовать dist/cyberx-vpn
  --sudoers-only    только настроить sudo (helper уже на месте)
  -h, --help        эта справка

При установке один раз запрашивается пароль sudo — дальше VPN
включается и выключается без повторных запросов.
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        --dev)
            DEV_MODE=1
            shift
            ;;
        --skip-build)
            SKIP_BUILD=1
            shift
            ;;
        --sudoers-only)
            SUDOERS_ONLY=1
            shift
            ;;
        -h | --help)
            usage
            exit 0
            ;;
        *)
            echo "Неизвестный аргумент: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

install_sudoers() {
    local helper="$1"
    local user="${SUDO_USER:-$(whoami)}"
    local tmp sudoers="/etc/sudoers.d/cyberx-vpn"

    if [ ! -x "$helper" ]; then
        echo "ERROR: helper не найден или не исполняемый: $helper" >&2
        exit 1
    fi

    if sudo -n true 2>/dev/null; then
        tmp="$(mktemp)"
        cat >"$tmp" <<EOF
# CyberX VPN — passwordless helper for $user
# Удаляется через: sudo rm $sudoers
$user ALL=(root) NOPASSWD: $helper up
$user ALL=(root) NOPASSWD: $helper down
$user ALL=(root) NOPASSWD: $helper status
EOF
        sudo install -m440 "$tmp" "$sudoers"
        rm -f "$tmp"
        sudo visudo -cf "$sudoers"
        echo "sudoers: $sudoers (пользователь $user, helper $helper)"
        return
    fi

    echo "запрос прав через pkexec (один раз)..."
    pkexec env INSTALL_DIR="$INSTALL_DIR" "$ROOT/tools/setup-privileges.sh"
}

secure_helper_binaries() {
    local dir="$1"
    if sudo -n true 2>/dev/null; then
        sudo chown root:root "$dir/helper.sh" "$dir/sing-box"
        sudo chmod 755 "$dir/helper.sh" "$dir/sing-box"
    fi
}

install_desktop() {
    local app_dir="$1"
    local exec_path="$2"
    local apps="$HOME/.local/share/applications"
    local icons="$HOME/.local/share/icons/hicolor/256x256/apps"

    mkdir -p "$apps" "$icons"
    sed -e "s|__APP_DIR__|$app_dir|g" -e "s|__EXEC__|$exec_path|g" \
        "$ROOT/CyberXVPN.desktop" >"$apps/cyberx-vpn.desktop"
    chmod +x "$apps/cyberx-vpn.desktop"
    if [ -f "$app_dir/assets/cyberx_mark.png" ]; then
        cp "$app_dir/assets/cyberx_mark.png" "$icons/cyberx-vpn.png"
    elif [ -f "$ROOT/assets/cyberx_mark.png" ]; then
        cp "$ROOT/assets/cyberx_mark.png" "$icons/cyberx-vpn.png"
    fi
    echo "ярлык: $apps/cyberx-vpn.desktop"
}

if [ "$SUDOERS_ONLY" = 1 ]; then
    HELPER="$(readlink -f "$INSTALL_DIR/helper.sh")"
    install_sudoers "$HELPER"
    secure_helper_binaries "$INSTALL_DIR"
    exit 0
fi

mkdir -p "$INSTALL_DIR"

if [ "$DEV_MODE" = 1 ]; then
    echo "режим разработки: $ROOT"
    if [ ! -x "$ROOT/sing-box" ]; then
        echo "скачиваем sing-box..."
        "$ROOT/tools/fetch_singbox.sh"
    fi
    ln -sf "$ROOT/helper.sh" "$INSTALL_DIR/helper.sh"
    ln -sf "$ROOT/sing-box" "$INSTALL_DIR/sing-box"
    cp -r "$ROOT/assets" "$INSTALL_DIR/"
    cat >"$INSTALL_DIR/run-dev.sh" <<EOF
#!/bin/bash
cd "$ROOT" && exec "$ROOT/run.sh"
EOF
    chmod +x "$INSTALL_DIR/run-dev.sh"
    install_desktop "$INSTALL_DIR" "$INSTALL_DIR/run-dev.sh"
    HELPER="$(readlink -f "$ROOT/helper.sh")"
    install_sudoers "$HELPER"
    secure_helper_binaries "$ROOT"
    echo ""
    echo "Готово. Запуск: $ROOT/run.sh"
    exit 0
fi

if [ "$SKIP_BUILD" = 0 ]; then
    if [ ! -x "$ROOT/.venv/bin/pyinstaller" ]; then
        echo "ERROR: нужен .venv с pyinstaller (см. README)" >&2
        exit 1
    fi
    if [ ! -x "$ROOT/sing-box" ]; then
        "$ROOT/tools/fetch_singbox.sh"
    fi
    echo "сборка PyInstaller..."
    "$ROOT/.venv/bin/pyinstaller" --noconfirm "$ROOT/cyberx-vpn.spec"
fi

DIST="$ROOT/dist/cyberx-vpn"
if [ ! -d "$DIST" ]; then
    echo "ERROR: нет $DIST — сначала соберите бандл" >&2
    exit 1
fi

(
    cd "$DIST"
    cp -r _internal/helper.sh _internal/sing-box _internal/assets . 2>/dev/null || true
    chmod +x helper.sh sing-box 2>/dev/null || true
)

echo "копирование в $INSTALL_DIR..."
rsync -a --delete \
    --exclude runtime \
    "$DIST/" "$INSTALL_DIR/"

install_desktop "$INSTALL_DIR" "$INSTALL_DIR/cyberx-vpn"
HELPER="$(readlink -f "$INSTALL_DIR/helper.sh")"
install_sudoers "$HELPER"
secure_helper_binaries "$INSTALL_DIR"

echo ""
echo "Готово: $INSTALL_DIR/cyberx-vpn"
echo "Пароль sudo больше не потребуется при подключении/отключении VPN."
