# Coding Health Guard 1.0.1

Aplikasi pengingat coding berbahasa Indonesia untuk Ubuntu 24.04 Desktop. Python 3 + GTK 3; instalasi per pengguna, tanpa PAM, tanpa service root, tanpa menghentikan VS Code/terminal. Tidak membaca password login.

## Instalasi

Ekstrak arsip, buka Terminal di folder hasil ekstrak:

```sh
./install.sh
~/.local/bin/coding-health-guard
```

Untuk memperbarui versi lama, jalankan `~/.local/bin/coding-health-guard --recover`, tunggu 3 detik, lalu jalankan installer baru dan buka aplikasi kembali. Pemulihan mengatur timer ke idle; pengaturan tetap disimpan.

Installer meminta sudo hanya untuk dependensi Ubuntu bila belum tersedia. Membuat launcher menu aplikasi dan autostart setelah login desktop. Tidak langsung menjalankan atau mengunci layar saat instalasi. Tray memakai protokol StatusNotifierItem/DBusMenu, tanpa fallback XEmbed atau dependensi libappindicator. Jika ekstensi tray belum tersedia pada GNOME:

```sh
sudo apt install gnome-shell-extension-appindicator
gnome-extensions enable ubuntu-appindicators@ubuntu.com
```

GNOME membutuhkan ekstensi AppIndicator aktif. Tanpa tray, buka launcher menu aplikasi lagi untuk menampilkan jendela yang tersembunyi.

## Pemakaian

Saat login ada pertanyaan apakah baru coding/sudah istirahat. Pilih **Mulai — sudah istirahat**, **Belum istirahat** untuk langsung mengambil jeda, atau **Lanjut sesi** untuk mempertahankan timer tersimpan. Jika tidak ada sesi, pilih Mulai. Setelah jeda selesai aplikasi menunggu konfirmasi mulai berikutnya.

Default coding 60 menit, hitung mundur 120 detik untuk menyimpan pekerjaan, jeda 10 menit, jeda panjang 20 menit setiap 3 sesi. Angka dapat diubah melalui Pengaturan. Pengingat setelah 8 dan 10 jam coding teramati per hari kalender lokal juga dapat diubah. Ini pengingat kebiasaan yang dapat disesuaikan, bukan pengukuran aktivitas editor atau anjuran medis.

Mode standar menyediakan Lewati dan Tunda (default 5 menit). Mode keras meniadakan keduanya, menonaktifkan perubahan pengaturan/restart timer saat sesi aktif, meminta GNOME mengunci sesi setelah countdown, dan menampilkan overlay sampai jeda selesai ketika layar dibuka. Password tetap ditangani Ubuntu. Tidak mencoba unlock otomatis. Proses dan dokumen lain tetap hidup.

State/config disimpan atomik di `${XDG_STATE_HOME:-~/.local/state}/coding-health-guard/` dengan izin file 600. Deadline bertahan restart/login ulang. Waktu offline/suspend memenuhi durasi jeda; tidak mengulang kunci pada setiap peluncuran. Coding harian hanya menghitung detik yang teramati saat program berjalan, bukan lama logout/suspend; bukan audit produktivitas. Jam sistem yang diubah dapat mengubah deadline. Hitungan sesi terus tersimpan lintas hari. Penguncian mempertahankan proses editor/terminal; logout atau reboot mengikuti perilaku Ubuntu yang biasa.

## Batas keamanan dan desktop

GTK berjalan di X11 dan Wayland. Permintaan kunci menggunakan GNOME ScreenSaver D-Bus secara asynchronous, kemudian loginctl untuk sesi saat ini jika tersedia. Aplikasi mengikuti sinyal layar kunci, memeriksa GetActive setelah permintaan, dan menampilkan permintaan Super+L jika gagal atau tidak terkonfirmasi. Aktifkan fitur penguncian layar Ubuntu. Pengujian development memverifikasi GetActive dan LockedHint pada GNOME X11/Wayland; konfigurasi desktop lain tetap bergantung pada dukungan pengelola sesi.

Pada X11, overlay fullscreen diminta per monitor. Pada Wayland, overlay memakai jendela tanpa bingkai yang dimaksimalkan untuk memakai perilaku jendela yang lebih konservatif pada compositor; panel sistem dapat tetap terlihat dan compositor menentukan posisi/fokusnya. Pada X11 pengelola jendela dapat mengubah fullscreen/always-on-top. Wayland membatasi fokus, posisi dan topmost; Alt+Tab, workspace, monitor tambahan atau compositor dapat melewati overlay. Overlay diperbarui saat GTK melaporkan monitor ditambah/dilepas; perilaku hotplug perangkat fisik belum diuji. Ini alat disiplin pribadi, bukan kiosk/kontrol akses: pengguna dapat menghentikan proses, mengedit state atau menonaktifkan autostart. Mode keras tidak menyediakan tombol skip biasa, tetapi tidak menjanjikan pemblokiran OS yang tak dapat dilewati.

Dokumentasi: https://gnome.pages.gitlab.gnome.org/gtk/gtk3/wayland.html dan https://gnome.pages.gitlab.gnome.org/gtk/gtk3/class.Window.html .

## Pemulihan aman

Klik overlay agar fokus, lalu tahan Ctrl+Shift+Esc selama 5 detik untuk mengakhiri aplikasi dan mengatur timer ke idle. Gunakan hanya untuk darurat. Jika tidak merespons, buka Terminal/TTY (Ctrl+Alt+F3, login sendiri):

```sh
~/.local/bin/coding-health-guard --recover
```

Tunggu 3 detik. Ini meminta proses GUI berhenti dan reset timer tanpa menyentuh aplikasi lain. Bila GUI macet, hapus autostart lalu logout/login; file recovery diproses saat peluncuran berikutnya:

```sh
rm -f ~/.config/autostart/coding-health-guard.desktop
```

Tidak ada penguncian permanen; layar Ubuntu selalu dapat dibuka lewat mekanisme Ubuntu yang normal. Tidak ada restart paksa atau logout otomatis.

## Uninstall

```sh
~/.local/share/coding-health-guard/uninstall.sh
```

Atau `./uninstall.sh` dari paket. State sengaja dipertahankan; untuk menghapusnya setelah aplikasi berhenti, hapus folder state di atas. Dependensi sistem tidak dihapus.

## Pengujian development

```sh
python3 -m unittest -v
python3 -m py_compile guard.py
sh -n install.sh uninstall.sh
# Dengan GTK terpasang; display terisolasi dan kunci OS dimock:
xvfb-run -a python3 gui_smoke.py -v
python3 installer_smoke.py
```

Lihat VALIDATION.md untuk hasil aktual dan TESTING.md untuk prosedur pengujian GNOME yang dapat diulang. Sebelum penggunaan rutin, uji dengan coding 1 menit, countdown 5 detik dan jeda 1 menit. Pastikan countdown, kunci native, overlay setelah unlock, recovery, multi-monitor, logout/login dan uninstall pada X11 serta Wayland target. Simpan pekerjaan dahulu. Tidak menggunakan database atau jaringan saat runtime.
