"""Installer lifecycle test with isolated HOME; GTK dependencies must exist."""
import os
from pathlib import Path
import subprocess
import tempfile

with tempfile.TemporaryDirectory(prefix='chg-install-') as tmp:
    env=dict(os.environ,HOME=tmp,XDG_STATE_HOME=tmp+'/state')
    subprocess.run(['sh','install.sh'],env=env,check=True)
    home=Path(tmp)
    launcher=home/'.local/bin/coding-health-guard'
    assert launcher.exists()
    desktop=home/'.config/autostart/coding-health-guard.desktop'
    assert 'X-GNOME-Autostart-enabled=true' in desktop.read_text()
    subprocess.run([str(launcher),'--recover'],env=env,check=True)
    assert (home/'state/coding-health-guard/recover').exists()
    subprocess.run(['sh',str(home/'.local/share/coding-health-guard/uninstall.sh')],env=env,check=True)
    assert not desktop.exists() and not launcher.exists()
    assert not (home/'.local/share/coding-health-guard').exists()
    assert (home/'state/coding-health-guard').exists()
print('PASS: install, launcher, autostart, recovery request, uninstall, state preservation')
