#!/bin/bash
# Root-хелпер CyberX VPN: подъём/остановка TUN-режима.
# Вызывается от root из GUI (sudo или pkexec). Делает только: запуск/останов sing-box
# и подмену/восстановление /etc/resolv.conf.
set -u

DIR="$(dirname "$(readlink -f "$0")")"
RUNTIME="$DIR/runtime"
PIDFILE="$RUNTIME/sing-box.pid"
IF="cyberx0"

die() { echo "ERROR: $1" >&2; exit 1; }

case "${1:-}" in
up)
    [ -f "$RUNTIME/singbox.json" ] || die "нет $RUNTIME/singbox.json"
    [ -f "$PIDFILE" ] && kill "$(cat "$PIDFILE")" 2>/dev/null
    pkill -x sing-box 2>/dev/null
    sleep 0.5
    [ -f /etc/resolv.conf ] && [ ! -f "$RUNTIME/resolv.conf.bak" ] && \
        cp /etc/resolv.conf "$RUNTIME/resolv.conf.bak"
    nohup "$DIR/sing-box" run -c "$RUNTIME/singbox.json" \
        > "$RUNTIME/sing-box.log" 2>&1 &
    echo $! > "$PIDFILE"
    for _ in $(seq 1 20); do
        ip link show "$IF" >/dev/null 2>&1 && break
        sleep 0.5
    done
    ip link show "$IF" >/dev/null 2>&1 || die "интерфейс $IF не поднялся, смотрите $RUNTIME/sing-box.log"
    printf 'nameserver 1.1.1.1\nnameserver 1.0.0.1\n' > /etc/resolv.conf
    echo "UP $IF"
    ;;
down)
    [ -f "$PIDFILE" ] && kill "$(cat "$PIDFILE")" 2>/dev/null && rm -f "$PIDFILE"
    pkill -x sing-box 2>/dev/null
    [ -f "$RUNTIME/resolv.conf.bak" ] && cp "$RUNTIME/resolv.conf.bak" /etc/resolv.conf
    echo "DOWN"
    ;;
status)
    ip link show "$IF" >/dev/null 2>&1 && echo "UP" || echo "DOWN"
    ;;
*)
    die "использование: helper.sh up|down|status"
    ;;
esac
