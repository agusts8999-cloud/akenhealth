"""GNOME end-to-end test. Only for the disposable chg-gnome-lab VM.

Run inside the real desktop user's session. A separate VM-console controller
must unlock with the test user's password and hold the documented recovery key
when this test emits the corresponding status files. No lock function is mocked.
"""
import json
import hashlib
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

if socket.gethostname()!='chg-gnome-lab' or os.environ.get('CHG_E2E_ALLOW_LOCK')!='1':
    raise SystemExit('Refusing: requires disposable development VM and CHG_E2E_ALLOW_LOCK=1')
import pyatspi
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,Gdk,Gio,GLib
Gtk.init([])
import guard

OUT=Path.home()/'chg-evidence'; OUT.mkdir(exist_ok=True)
STATE=guard.ROOT
BACKEND=os.environ['XDG_SESSION_TYPE']
REPORT={'tray_sha256':hashlib.sha256(Path('tray.py').read_bytes()).hexdigest(),'backend':BACKEND,'gdk_display':Gdk.Display.get_default().__gtype__.name,'gnome':subprocess.check_output(['gnome-shell','--version'],text=True).strip(),'source_sha256':hashlib.sha256(Path(guard.__file__).read_bytes()).hexdigest(),'checks':[]}
assert ('Wayland' if BACKEND=='wayland' else 'X11') in REPORT['gdk_display']

def record(name):
    REPORT['checks'].append(name)
    (OUT/(BACKEND+'-report.json')).write_text(json.dumps(REPORT,indent=2))
    print('PASS:',name,flush=True)

def wait(check,timeout=20):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        try:
            result=check()
            if result:return result
        except GLib.Error: pass
        time.sleep(.25)
    raise AssertionError('Timed out: '+getattr(check,'__name__',str(check)))

def state(): return guard.read(STATE/'state.json',{})
def descendants(node):
    yield node
    try:
        for child in node:
            if child: yield from descendants(child)
    except Exception: pass

def nodes():
    result=[]
    for app in pyatspi.Registry.getDesktop(0):
        try:
            if app and app.name in ('guard.py','coding-health-guard','Coding Health Guard'): result.extend(descendants(app))
        except GLib.Error: pass
    return result
def matching(name,roles):
    for node in nodes():
        try:
            if node.name==name and node.getRole() in roles: return node
        except GLib.Error: pass
    return None

def button(name):
    return matching(name,(pyatspi.ROLE_PUSH_BUTTON,))
def click(name):
    def ready():
        b=button(name)
        return b if b and b.getState().contains(pyatspi.STATE_SHOWING) and b.getState().contains(pyatspi.STATE_ENABLED) else None
    b=wait(ready)
    assert b.queryAction().doAction(0),'Button action rejected: '+name

def window(title):
    return matching(title,(pyatspi.ROLE_FRAME,pyatspi.ROLE_WINDOW,pyatspi.ROLE_DIALOG))

def launch():
    subprocess.run(['gtk-launch','coding-health-guard'],check=True)
    wait(lambda:window('Coding Health Guard'))

def recover():
    subprocess.run([str(Path.home()/'.local/bin/coding-health-guard'),'--recover'],check=True)
    wait(lambda:state().get('phase')=='idle')
    wait(lambda:not window('Coding Health Guard'))

def seed(phase,hard=False,seconds=8):
    (STATE/'recover').unlink(missing_ok=True)
    (STATE/'show').unlink(missing_ok=True)
    config=guard.DEFAULTS.copy();config.update(hard=hard,countdown=8,short=1,long=1)
    guard.save(STATE/'config.json',config)
    guard.save(STATE/'state.json',dict(phase=phase,deadline=time.time()+seconds,sessions=0,day='',total=0,last=time.time(),warned=[]))

def locked():
    out=subprocess.check_output(['gdbus','call','--session','--dest','org.gnome.ScreenSaver','--object-path','/org/gnome/ScreenSaver','--method','org.gnome.ScreenSaver.GetActive'],text=True)
    return 'true' in out

try:
    for marker in OUT.glob(BACKEND+'-await-*'): marker.unlink()
    if window('Coding Health Guard'): recover()
    subprocess.run(['sh','install.sh'],check=True)
    assert (Path.home()/'.local/share/coding-health-guard/guard.py').read_bytes()==Path(guard.__file__).read_bytes()
    assert (Path.home()/'.local/share/coding-health-guard/tray.py').read_bytes()==Path('tray.py').read_bytes()
    seed('idle');launch()
    assert button('Mulai — sudah istirahat') and button('Belum istirahat') and button('Lanjut sesi')
    record('launcher and Indonesian startup choices')
    click('Pengaturan')
    dialog=wait(lambda:window('Pengaturan (berlaku sesi berikutnya)'))
    def spins_ready():
        spins=[n for n in descendants(dialog) if n.getRole()==pyatspi.ROLE_SPIN_BUTTON]
        return spins if len(spins)==6 else None
    spins=wait(spins_ready)
    for spin,value in zip(spins,[1,3,1,2,3,1]): spin.queryValue().currentValue=value
    entry=next(n for n in descendants(dialog) if n.getRole()==pyatspi.ROLE_TEXT)
    entry.queryEditableText().setTextContents('7,9')
    click('Simpan')
    wait(lambda:guard.read(STATE/'config.json',{}).get('reminders')==[7.,9.])
    assert guard.read(STATE/'config.json',{})['work']==1
    record('GUI saves configurable durations and daily reminders')
    bus=Gio.bus_get_sync(Gio.BusType.SESSION,None)
    def prop(destination,path,interface,key):
        reply=bus.call_sync(destination,path,'org.freedesktop.DBus.Properties','Get',GLib.Variant('(ss)',(interface,key)),None,Gio.DBusCallFlags.NONE,2000,None)
        return reply.unpack()[0]
    tray_identity=[]
    def tray_registered():
        try:
            items=prop('org.kde.StatusNotifierWatcher','/StatusNotifierWatcher','org.kde.StatusNotifierWatcher','RegisteredStatusNotifierItems')
            for item in items:
                service,_,path=item.partition('@')
                if not path:
                    service,_,path=item.partition('/')
                    path='/'+path
                if prop(service,path,'org.kde.StatusNotifierItem','Id')=='coding-health-guard':
                    tray_identity[:]=[service,path];return True
        except GLib.Error: pass
        return False
    wait(tray_registered)
    record('system tray registers Coding Health Guard with GNOME AppIndicator')
    service,item_path=tray_identity
    menu_path=prop(service,item_path,'org.kde.StatusNotifierItem','Menu')
    layout=bus.call_sync(service,menu_path,'com.canonical.dbusmenu','GetLayout',GLib.Variant('(iias)',(0,-1,[])),None,Gio.DBusCallFlags.NONE,2000,None)
    assert 'Buka Coding Health Guard' in str(layout)
    click('Sembunyikan')
    bus.call_sync(service,menu_path,'com.canonical.dbusmenu','Event',GLib.Variant('(isvu)',(1,'clicked',GLib.Variant('i',0),0)),None,Gio.DBusCallFlags.NONE,2000,None)
    wait(lambda:(win:=window('Coding Health Guard')) and win.getState().contains(pyatspi.STATE_SHOWING))
    record('tray menu layout and open action work')
    click('Mulai — sudah istirahat');wait(lambda:state()['phase']=='work')
    record('start coding from GUI')
    click('Sembunyikan');time.sleep(1)
    subprocess.run(['gtk-launch','coding-health-guard'],check=True)
    wait(lambda:(win:=window('Coding Health Guard')) and win.getState().contains(pyatspi.STATE_SHOWING))
    record('relaunch activates existing hidden window')
    recover();record('CLI recovery exits and resets timer')
    seed('work');launch();wait(lambda:state()['phase']=='countdown')
    assert button('Tunda').getState().contains(pyatspi.STATE_SHOWING)
    click('Tunda');wait(lambda:state()['phase']=='work')
    record('standard countdown and snooze')
    click('Belum istirahat');wait(lambda:state()['phase']=='break')
    click('Lewati istirahat');wait(lambda:state()['phase']=='work')
    record('standard skip break')
    recover()
    # Keep a real terminal child alive while GNOME locks/unlocks.
    subprocess.run(['gnome-terminal','--','sh','-c','echo "Coding Health Guard process preservation test"; sleep 900'],check=True)
    time.sleep(2)
    sentinel=subprocess.check_output(['pgrep','-u',str(os.getuid()),'-f','^sleep 900$'],text=True).splitlines()
    assert sentinel
    document=Path.home()/'coding-health-guard-preserve.txt'
    document.write_text('Development test: preserve this VS Code window during lock/unlock.\n')
    code_log=(OUT/(BACKEND+'-code.log')).open('ab')
    subprocess.Popen(['code','--new-window','--disable-extensions',str(document)],stdin=subprocess.DEVNULL,stdout=code_log,stderr=code_log)
    def find_code():
        pids=[]
        for proc in Path('/proc').iterdir():
            if not proc.name.isdigit(): continue
            try:
                args=(proc/'cmdline').read_bytes().split(b'\0')
                if args and args[0].split(b' ',1)[0]==b'/usr/share/code/code' and not any(b'--type=' in a or b'cli.js' in a for a in args): pids.append(int(proc.name))
            except OSError: pass
        return pids
    code_pids=wait(find_code,40)
    record('real GNOME terminal and VS Code opened')
    seed('work',True);launch()
    wait(lambda:state()['phase']=='countdown')
    assert not button('Tunda').getState().contains(pyatspi.STATE_SHOWING)
    assert not button('Pengaturan').getState().contains(pyatspi.STATE_ENABLED)
    record('hard mode hides skip/snooze and disables settings')
    wait(locked,25)
    sid=os.environ['XDG_SESSION_ID']
    wait(lambda:subprocess.check_output(['loginctl','show-session',sid,'-p','LockedHint','--value'],text=True).strip()=='yes')
    record('native GNOME lock confirmed by GetActive and logind LockedHint')
    (OUT/(BACKEND+'-await-unlock')).touch()
    wait(lambda:not locked(),90)
    wait(lambda:window('Waktunya istirahat'))
    assert state()['phase']=='break'
    record('password unlock returns to active break overlay')
    wait(tray_registered);record('tray registers again after GNOME unlock')
    (OUT/(BACKEND+'-overlay-ready')).touch()
    wait(lambda:state()['phase']=='idle',90)
    wait(lambda:not window('Waktunya istirahat'))
    for pid in sentinel+code_pids:os.kill(int(pid),0)
    record('break completes, overlays close, terminal child and VS Code survive')
    recover()
    seed('break',True,60);launch();wait(lambda:window('Waktunya istirahat'))
    assert not locked()
    record('resumed break persists without relocking desktop')
    (OUT/(BACKEND+'-await-recovery-key')).touch()
    wait(lambda:state()['phase']=='idle',30)
    wait(lambda:not window('Coding Health Guard'))
    record('real keyboard Ctrl+Shift+Esc held 5 seconds recovers')
    subprocess.run(['sh',str(Path.home()/'.local/share/coding-health-guard/uninstall.sh')],check=True)
    assert not (Path.home()/'.config/autostart/coding-health-guard.desktop').exists()
    record('uninstall removes desktop autostart')
    REPORT['result']='PASS'
except Exception as exc:
    REPORT['result']='FAIL';REPORT['error']=repr(exc)
    raise
finally:
    (OUT/(BACKEND+'-report.json')).write_text(json.dumps(REPORT,indent=2))
