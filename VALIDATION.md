# Validasi development — 18 Oktober 2026

Environment: ubuntu@aken-dev (hostname ubuntu), Ubuntu 24.04.5, Python 3.12.3, repository /home/ubuntu/projects/coding-health-guard, branch main. Tidak ada database. Semua state test memakai direktori temporary; tidak memakai desktop production.

- `python3 -m unittest -v`: PASS, 11 pengujian logika timer, persistence, konfigurasi, snooze, jeda panjang, kegagalan/sukses permintaan kunci (mock).
- `python3 -m py_compile guard.py gui_smoke.py installer_smoke.py`: PASS.
- `sh -n install.sh uninstall.sh`: PASS.
- `python3 gui_smoke.py -v` pada Xvfb :87 dengan GTK 3.24.41: PASS, alur mulai, countdown, snooze, mode keras, pengaturan terkunci, overlay, recovery dan reset state. Fungsi lock native dimock: tidak mengunci sesi development.
- `python3 installer_smoke.py`: PASS, instalasi HOME terisolasi, launcher, autostart, permintaan recovery, uninstall dan preservasi state.
- `git diff --check`: PASS sebelum commit.

Karena tidak tersedia sudo noninteraktif, library GTK dan Xvfb Ubuntu diunduh dan diekstrak khusus ke /tmp/chg-gtk pada development. GI_TYPELIB_PATH dan LD_LIBRARY_PATH diarahkan ke library sementara. Xvfb memakai compiler keymap dari direktori sementara. Ini hanya infrastruktur test; tidak dibundel dalam aplikasi. Desktop pengguna memasang paket GTK resmi melalui apt.

## Cakupan belum terbukti

Penguncian GNOME native dan unlock sungguhan, Wayland compositor, tray dengan ekstensi GNOME, monitor ganda/hotplug, autostart login desktop nyata, serta pemeriksaan visual pada perangkat pengguna belum diuji. Xvfb tidak membuktikan kebijakan fokus/fullscreen GNOME. Paket ini kandidat uji development, bukan release production yang dinyatakan PASS. Status kelayakan production: BLOCKED sampai checklist desktop nyata selesai. Tidak ada deployment production.

Checklist desktop (X11 dan Wayland): atur coding 1 menit/countdown 5 detik/jeda 1 menit; uji konfirmasi login, countdown, standar skip/snooze, hard tanpa skip, native lock, unlock ke overlay, selesai jeda, recovery keyboard/TTY, relogin saat jeda, tray/tanpa tray, dua monitor dan uninstall. Jangan tandai PASS hanya dari mock atau permintaan lock yang return sukses.

Commit source diidentifikasi oleh SOURCE_COMMIT.txt yang disertakan saat pengemasan dari Git, dan history repository. Paket dibangun dari commit tersebut di development, bukan working tree.
