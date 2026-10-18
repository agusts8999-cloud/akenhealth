"""Verify autostart/persistence after a real GDM logout/login in the lab."""
import hashlib
import json
import os
from pathlib import Path
import socket
import time
import gi
if socket.gethostname()!='chg-gnome-lab' or os.environ.get('CHG_E2E_ALLOW_LOCK')!='1':
    raise SystemExit('Requires disposable development VM')
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,Gdk,GLib
import pyatspi
import guard
Gtk.init([])
expected=json.loads((Path.home()/'chg-evidence/relogin-expected.json').read_text())
end=time.monotonic()+40
count=0
while time.monotonic()<end:
    count=0
    try:
        for app in pyatspi.Registry.getDesktop(0):
            if not app or app.name not in ('guard.py','coding-health-guard','Coding Health Guard'):continue
            for win in app:
                if win.name=='Waktunya istirahat' and win.getState().contains(pyatspi.STATE_SHOWING): count+=1
    except GLib.Error: pass
    state=guard.read(guard.ROOT/'state.json',{})
    if count and state.get('phase')=='break':break
    time.sleep(.5)
assert state['deadline']==expected['deadline'],(state,expected)
assert state['phase']=='break' and count==Gdk.Display.get_default().get_n_monitors()
backend=os.environ['XDG_SESSION_TYPE']
report=dict(tray_sha256=hashlib.sha256((Path.home()/'.local/share/coding-health-guard/tray.py').read_bytes()).hexdigest(),backend=backend,gdk_display=Gdk.Display.get_default().__gtype__.name,result='PASS',autostart=True,persisted_deadline=True,overlay_count=count,source_sha256=hashlib.sha256((Path.home()/'.local/share/coding-health-guard/guard.py').read_bytes()).hexdigest())
(Path.home()/'chg-evidence'/(backend+'-relogin.json')).write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
