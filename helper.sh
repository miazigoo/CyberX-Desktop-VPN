#!/bin/bash
# Системный помощник. GUI передаёт конфигурацию через stdin при действии up.
set -euo pipefail
umask 077
PATH=/usr/sbin:/usr/bin:/sbin:/bin
DIR=/usr/local/lib/cyberx-vpn
ENGINE="$DIR/sing-box"
STATE=/run/cyberx-vpn
IF=cyberx0
die() { echo "Ошибка: $*" >&2; exit 1; }

[[ $(readlink -f "$0") == "$DIR/helper.sh" ]] || die "Запустите ./tools/install.sh и используйте установленный помощник."
[[ $(id -u) == 0 ]] || die "Для управления туннелем нужны права администратора."
install -d -m700 "$STATE"
exec 9>"$STATE/lock"
flock -w 15 9 || die "Другая операция с VPN ещё выполняется."

owns_process() {
    [[ -f "$STATE/pid" ]] || return 1
    read -r pid < "$STATE/pid" || return 1
    [[ $pid =~ ^[1-9][0-9]*$ && $(readlink "/proc/$pid/exe") == "$ENGINE" ]]
}

stop_tunnel() {
    local pid
    if owns_process; then
        kill "$pid" || true
        for ((i=0; i<50; i++)); do
            owns_process || break
            sleep 0.1
        done
        if owns_process; then
            die "sing-box всё ещё работает. Проверьте $STATE/sing-box.log."
        fi
    fi
    if [[ -f "$STATE/resolv.conf.bak" ]]; then
        # Сетевой менеджер мог заменить DNS после подключения.
        if cmp -s /etc/resolv.conf "$STATE/vpn-resolv.conf"; then
            cat "$STATE/resolv.conf.bak" > /etc/resolv.conf
        fi
        rm -f "$STATE/resolv.conf.bak" "$STATE/vpn-resolv.conf"
    fi
    rm -f "$STATE/pid" "$STATE/singbox.json"
}

case "${1:-}" in
    up)
        if ip link show "$IF" >/dev/null 2>&1; then
            die "Интерфейс $IF уже используется."
        fi
        stop_tunnel
        trap 'stop_tunnel' EXIT
        cat > "$STATE/singbox.json"
        "$ENGINE" check -c "$STATE/singbox.json" >&2
        nohup "$ENGINE" run -c "$STATE/singbox.json" </dev/null >"$STATE/sing-box.log" 2>&1 9>&- &
        echo $! > "$STATE/pid"
        for ((i=0; i<40; i++)); do
            ip link show "$IF" >/dev/null 2>&1 && break
            kill -0 "$!" 2>/dev/null || break
            sleep 0.25
        done
        ip link show "$IF" >/dev/null 2>&1 || die "Интерфейс $IF не поднялся. Подробности: $STATE/sing-box.log."
        if grep -Eq '^[[:space:]]*nameserver[[:space:]]+127\.0\.0\.(53|54)([[:space:]]|$)' /etc/resolv.conf \
            && [[ -f /run/systemd/resolve/stub-resolv.conf ]]; then
            resolvectl dns "$IF" 1.1.1.1 1.0.0.1
            resolvectl domain "$IF" '~.'
        else
            cp -L /etc/resolv.conf "$STATE/resolv.conf.bak"
            printf 'nameserver 1.1.1.1\nnameserver 1.0.0.1\n' > "$STATE/vpn-resolv.conf"
            cat "$STATE/vpn-resolv.conf" > /etc/resolv.conf
        fi
        trap - EXIT
        echo "UP $IF"
        ;;
    down) stop_tunnel; echo "DOWN" ;;
    status) if owns_process && ip link show "$IF" >/dev/null 2>&1; then echo "UP"; else echo "DOWN"; fi ;;
    *) die "Использование: helper.sh up|down|status" ;;
esac
