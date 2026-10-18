# Aturan proyek
Development: ubuntu@aken-dev:/home/ubuntu/projects/coding-health-guard. VM desktop development: chg-gnome-lab, dijalankan melalui KVM di /home/ubuntu/chg-desktop-lab pada aken-dev; source uji /home/guard/chg-src. Workstation hanya koordinasi dan menerima paket. Production: desktop Ubuntu pengguna; tidak ada deployment production yang diotorisasi dalam pekerjaan pembuatan paket.

1. Semua source/config/refactor/dependency/build release hanya di development; tidak mengedit source atau commit langsung di production.
2. Uji di development dengan data terisolasi; test gagal/tidak terbukti berarti release FAIL/BLOCKED.
3. Hanya source yang test PASS dan commit Git teridentifikasi boleh dirilis; catat SHA, perintah, hasil dan cakupan yang belum diuji. Tidak bypass check.
4. Production hanya smoke/health/log minimum; temuan direproduksi dan diperbaiki di development. Rollback hanya release sebelumnya yang teruji.
5. Perbaikan production wajib regression test, ulang test, commit, release dan verifikasi production sebelum dinyatakan selesai.
6. Setiap perubahan source/config wajib review diff, test, stage file tugas saja dan commit dengan identitas sah. Tidak commit secret/perubahan orang lain, --no-verify, force push atau reset/clean destruktif.

Sebelum perubahan/test verifikasi host, path, branch, status dan target environment. Tidak ada database. Test: python3 -m unittest -v; python3 -m py_compile guard.py; sh -n install.sh uninstall.sh. GTK smoke memerlukan display development. Build paket dari git archive commit yang diuji. Deployment pengguna melalui install.sh hanya jika diotorisasi; verifikasi pada desktop target.

Test desktop nyata: prosedur TESTING.md, desktop_e2e.py dan relogin_probe.py pada GNOME X11 serta Wayland di VM development terisolasi. Jangan menggunakan lock mock sebagai bukti kelulusan penguncian native. Build: python3 build_release.py VERSION DIREKTORI di working tree bersih sesudah commit.
