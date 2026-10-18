"""Overlay lifecycle stress on a disposable real GNOME session (no native lock)."""
import hashlib,json,os,socket,tempfile
from pathlib import Path
import gi
if socket.gethostname()!='chg-gnome-lab' or os.environ.get('CHG_E2E_ALLOW_LOCK')!='1':
    raise SystemExit('Disposable development VM only')
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,GLib,Gdk
import guard
root=Path(tempfile.mkdtemp(prefix='chg-overlay-stress-'))
t=guard.Timer(root);t.config['hard']=True;t.s.update(phase='break',deadline=t.now()+300)
step=[0];errors=[]
def check():
    try:
        windows=[w for w in Gtk.Window.list_toplevels() if w.get_title()=='Waktunya istirahat' and w.get_visible()]
        if step[0]%2==0:
            assert windows
            assert windows[0].get_focus()==windows[0].get_child()
            if os.environ['XDG_SESSION_TYPE']=='wayland':
                assert windows[0].get_window().get_state()&Gdk.WindowState.MAXIMIZED
            t.s['phase']='idle'
        else:
            assert not windows
            t.s.update(phase='break',deadline=t.now()+300)
        step[0]+=1
        if step[0]>=24:
            (root/'recover').touch();return False
        return True
    except Exception as exc:
        errors.append(repr(exc));Gtk.main_quit();return False
GLib.timeout_add(1500,check)
guard.run_gui(t)
report=dict(backend=os.environ['XDG_SESSION_TYPE'],cycles=step[0]//2,result='FAIL' if errors else 'PASS',errors=errors,source_sha256=hashlib.sha256(Path(guard.__file__).read_bytes()).hexdigest())
(Path.home()/'chg-evidence'/(report['backend']+'-stress.json')).write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
if errors:raise SystemExit(1)
