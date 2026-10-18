#!/bin/sh
set -eu
[ "$(id -u)" != 0 ] || { echo 'Jalankan sebagai pengguna desktop biasa, bukan root.'; exit 1; }
cd "$(dirname "$0")"
if ! /usr/bin/python3 -c 'import gi; gi.require_version("Gtk","3.0")' 2>/dev/null; then
    echo 'Memasang dependensi Ubuntu (memerlukan sudo)...'
    sudo apt-get update
    sudo apt-get install -y python3 python3-gi gir1.2-gtk-3.0 libglib2.0-bin
fi
base="$HOME/.local/share/coding-health-guard"
mkdir -p "$base" "$HOME/.local/bin" "$HOME/.local/share/applications" "$HOME/.config/autostart"
install -m 644 guard.py README.md "$base/"
install -m 755 uninstall.sh "$base/"
cat > "$HOME/.local/bin/coding-health-guard" <<'EOF'
#!/bin/sh
exec /usr/bin/python3 "$HOME/.local/share/coding-health-guard/guard.py" "$@"
EOF
chmod 755 "$HOME/.local/bin/coding-health-guard"
# Desktop Exec requires quoted paths, with reserved characters escaped.
/usr/bin/python3 - <<'EOF'
from pathlib import Path
home=Path.home()
exe=str(home/'.local/bin/coding-health-guard')
exe=exe.replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$').replace('%','%%')
text='[Desktop Entry]\nType=Application\nName=Coding Health Guard\nComment=Pengingat istirahat coding\nExec="'+exe+'"\nIcon=appointment-soon\nTerminal=false\nCategories=Utility;\nX-GNOME-Autostart-enabled=true\n'
for p in (home/'.local/share/applications/coding-health-guard.desktop',home/'.config/autostart/coding-health-guard.desktop'): p.write_text(text)
EOF
printf '%s\n' 'Terpasang. Buka Coding Health Guard dari menu aplikasi atau login desktop berikutnya.' 'Tray opsional: sudo apt install gir1.2-ayatanaappindicator3-0.1 (GNOME perlu ekstensi AppIndicator aktif).'
