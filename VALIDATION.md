# Validasi Coding Health Guard 1.0.1 — 18 Oktober 2026

Status: PASS pada cakupan development yang dijelaskan di bawah. Tidak ada deployment production.

## Environment

Source/build: ubuntu@aken-dev:/home/ubuntu/projects/coding-health-guard, branch main. VM development KVM/QEMU 8.2.2 bernama chg-gnome-lab, Ubuntu 24.04, GNOME Shell 46.0/Mutter 46.2, GTK 3.24.41, satu monitor virtual virtio, rendering software. Database tidak digunakan. User/password/key VM khusus pengujian; credential tidak disertakan dalam repository/paket.

## Hasil

- `python3 -m unittest -v`: PASS, 15 test logika timer/config/state dan wire format/menu tray.
- `python3 -m py_compile guard.py tray.py gui_smoke.py installer_smoke.py desktop_e2e.py relogin_probe.py overlay_stress.py build_release.py`: PASS.
- `sh -n install.sh uninstall.sh` dan `git diff --check`: PASS.
- `python3 gui_smoke.py -v` pada Xvfb development: PASS. Meliputi dialog pengaturan, timer tetap berjalan saat pengingat terbuka, mode keras, overlay yang dapat menerima fokus, dan recovery. Lock pada test ini dimock.
- `python3 installer_smoke.py`: PASS; HOME/state terisolasi, launcher, autostart, recovery, uninstall dan preservasi state.
- GNOME Wayland native: PASS, 18 pemeriksaan dalam evidence/wayland-report.json. Backend GdkWaylandDisplay, bukan XWayland.
- Wayland overlay stress: PASS, 12 siklus create/destroy; evidence/wayland-stress.json.
- Wayland logout/login GDM: PASS, autostart berjalan tanpa membuka launcher manual; deadline sama dan overlay kembali, evidence/wayland-relogin.json.
- GNOME X11 native: PASS, 18 pemeriksaan pada source yang sama dengan Wayland; backend GdkX11Display, evidence/x11-report.json.
- X11 overlay stress: PASS, 12 siklus; evidence/x11-stress.json.
- X11 logout/login GDM: PASS, autostart dan deadline tetap sama; evidence/x11-relogin.json.

Native E2E benar-benar meminta penguncian GNOME, memeriksa ScreenSaver.GetActive dan logind LockedHint, membuka layar memakai password akun uji lewat konsol VM, menunggu jeda satu menit penuh, serta memverifikasi PID terminal dan VS Code tetap hidup. Tidak menggunakan lock mock. Pengujian keyboard menggunakan input perangkat VM, dengan overlay difokuskan terlebih dahulu. Deadline coding dipercepat melalui state test; logika aplikasi tidak dipatch untuk meloloskan test. Detail prosedur: TESTING.md.

## Temuan dan perbaikan

- Pengingat harian memakai dialog nonmodal sehingga tidak menahan pembaruan timer.
- Permintaan kunci berjalan asynchronous, status layar diperiksa, dan overlay dipresentasikan lagi saat unlock.
- Overlay menerima fokus keyboard secara eksplisit; pemulihan Ctrl+Shift+Esc berhasil setelah overlay diklik.
- Tray menggunakan StatusNotifierItem/DBusMenu langsung, dengan registrasi ulang ketika watcher GNOME kembali. Tidak memakai GtkStatusIcon/XEmbed fallback yang menghasilkan GTK critical pada kandidat awal Wayland.
- Identitas aplikasi/ikon diperbaiki; state NaN/Infinity dipulihkan ke kondisi aman.
- X11 memakai overlay fullscreen; Wayland memakai jendela tanpa bingkai yang dimaksimalkan. Panel sistem dan kebijakan fokus tetap dikendalikan compositor.

Selama iterasi kandidat awal, sesi GNOME Wayland sempat mengalami SIGSEGV. Backtrace core menempatkan frame kegagalan pada libatk-bridge/g_object_ref dalam proses GNOME Shell, saat otomatisasi aksesibilitas berulang. Ini bukan bukti bahwa fullscreen adalah penyebabnya, dan aplikasi tidak mengklaim memperbaiki bug internal GNOME. Source final diuji ulang dengan E2E, stress overlay yang tidak membaca tree aksesibilitas, dan login ulang. Kejadian kandidat awal tidak dicatat sebagai hasil PASS.

## Batas cakupan

Pengujian ini memakai VM satu monitor. Monitor fisik ganda/hotplug, driver GPU perangkat pengguna, suspend/hibernate nyata, dan desktop selain GNOME belum divalidasi. Dukungan monitor per-penempatan pada Wayland bergantung compositor. Overlay adalah alat disiplin pribadi; bukan kiosk dan tidak mengubah pengamanan/PAM Ubuntu. Pengguna tetap dapat membuka layar dengan mekanisme Ubuntu serta memakai recovery. Tidak ada aplikasi lain yang dihentikan oleh guard.

Source yang diuji dicocokkan terhadap hash dalam report/manifest evidence sebelum commit dan pengemasan. Paket dibuat di development dari Git commit bersih dan menyertakan SOURCE_COMMIT.txt. Tidak ada deployment atau verifikasi production dalam tugas ini.
