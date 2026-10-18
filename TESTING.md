# Pengujian yang dapat diulang

Semua perintah dijalankan di development. Jangan menjalankan desktop_e2e.py pada desktop kerja atau production: test tersebut sengaja meminta kunci layar dan mengubah state aplikasi.

## Logika dan GUI terisolasi

```sh
python3 -m unittest -v
python3 -m py_compile guard.py tray.py gui_smoke.py installer_smoke.py desktop_e2e.py relogin_probe.py overlay_stress.py build_release.py
sh -n install.sh uninstall.sh
xvfb-run -a python3 gui_smoke.py -v
python3 installer_smoke.py
git diff --check
```

GUI smoke memakai lock mock; hasilnya tidak menggantikan test GNOME nyata. Test dialog pengingat memastikan timer tetap maju saat pengingat terbuka.

## VM desktop development

Gunakan VM KVM/QEMU Ubuntu 24.04 dengan hostname `chg-gnome-lab`, user biasa `guard` yang memiliki password uji, GDM, GNOME Shell, GTK 3, gjs, Xorg, Wayland, gnome-terminal, VS Code, python3-pyatspi dan gnome-shell-extension-appindicator. `gjs` diperlukan untuk layanan D-Bus ScreenSaver/Extensions pada pemasangan GNOME minimal. Password/key lab tidak disimpan dalam repository atau paket aplikasi.

Jalankan sesi desktop nyata dari GDM. Untuk X11 pilih sesi Xorg; untuk Wayland aktifkan Wayland pada GDM dan pilih sesi Wayland. Verifikasi `loginctl show-session ID -p Type` dan backend GDK yang dilaporkan test. Konfigurasi GDM hanya untuk VM development, bukan bagian installer aplikasi.

Dari terminal sesi desktop VM:

```sh
gsettings set org.gnome.desktop.interface toolkit-accessibility true
gsettings set org.gnome.desktop.session idle-delay 0
gnome-extensions enable ubuntu-appindicators@ubuntu.com
CHG_E2E_ALLOW_LOCK=1 python3 -u desktop_e2e.py
```

Penguncian idle dinonaktifkan hanya di VM agar yang diuji adalah kunci yang dipicu aplikasi. Jalankan test melalui terminal desktop atau pertahankan koneksi SSH penguji tetap hidup. Bila melalui SSH, gunakan environment display, D-Bus dan runtime dari sesi GNOME serta XDG_SESSION_ID sesi grafis, bukan ID sesi SSH.

Saat `~/chg-evidence/BACKEND-await-unlock` muncul, buka layar dari konsol VM dengan password akun uji. Test memeriksa GetActive dan LockedHint sebelum tahap ini. Saat marker `BACKEND-await-recovery-key` muncul, fokuskan overlay lalu tahan Ctrl+Shift+Esc selama sedikitnya 5 detik. Controller konsol otomatis harus memastikan sesi masih terkunci sebelum mengetik password; jangan menyimpan password di log/screenshot/argumen proses.

Hasil disimpan sebagai `~/chg-evidence/BACKEND-report.json`, termasuk hash SHA-256 source yang dijalankan. Test meliputi launcher, pengaturan GUI, tray, aktivasi ulang, standar skip/snooze, hard mode, kunci asli, unlock ke overlay, durasi jeda satu menit penuh, preservasi PID terminal/VS Code, pemulihan keyboard, dan uninstall. Deadline kerja dipercepat melalui state test; kode timer produksi tidak dimodifikasi atau dimock.

## Login ulang dan autostart

Setelah E2E selesai (aplikasi di-uninstall oleh test), install kembali. Dengan aplikasi berhenti, siapkan config hard dan state break dengan deadline beberapa menit ke depan, serta salin deadline itu ke `~/chg-evidence/relogin-expected.json` dalam format `{"deadline": ANGKA_YANG_SAMA}`. Hapus marker recovery lama dari state test sebelum menyiapkan sesi baru.

Logout/login dari GDM VM (atau restart GDM khusus VM). Jangan menjalankan launcher secara manual. Dari terminal desktop baru:

```sh
CHG_E2E_ALLOW_LOCK=1 python3 relogin_probe.py
```

Probe memastikan autostart membuka overlay, deadline tetap sama, backend sesuai sesi baru, dan jumlah overlay sesuai monitor. Simpan hasil BACKEND-relogin.json. Ulangi pada X11 dan Wayland. Pulihkan aplikasi dengan --recover sesudahnya.

## Stress overlay

Pada VM development dengan aplikasi utama berhenti, jalankan `CHG_E2E_ALLOW_LOCK=1 python3 overlay_stress.py`. Test membuat/menghapus overlay 12 siklus, memakai source UI asli, tanpa meminta lock OS, dan memastikan widget menerima fokus. Pada Wayland juga dipastikan overlay berstatus maximized. Simpan BACKEND-stress.json dan periksa PID/log GNOME sesudah test. Test ini melengkapi, bukan menggantikan, penguncian asli dalam E2E.

## Pengemasan

Setelah test PASS dan commit, jalankan dari working tree bersih:

```sh
python3 build_release.py 1.0.1 /path/development/releases
```

Builder mengambil source melalui git archive HEAD, memasukkan SOURCE_COMMIT.txt, membuat tar.gz/zip beserta checksum. Artefak tersebut yang disalin ke workstation; jangan membuat release dari working tree yang belum di-commit.
