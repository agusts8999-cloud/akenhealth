#!/bin/sh
set -eu
[ "$(id -u)" != 0 ] || { echo 'Jalankan sebagai pengguna desktop biasa.'; exit 1; }
"$HOME/.local/bin/coding-health-guard" --recover 2>/dev/null || true
sleep 3
rm -f "$HOME/.config/autostart/coding-health-guard.desktop" "$HOME/.local/share/applications/coding-health-guard.desktop" "$HOME/.local/bin/coding-health-guard"
rm -rf "$HOME/.local/share/coding-health-guard"
echo 'Aplikasi dihapus. State dipertahankan di ${XDG_STATE_HOME:-~/.local/state}/coding-health-guard.'
