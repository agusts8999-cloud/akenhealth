#!/usr/bin/python3
"""Coding Health Guard — local, per-user desktop break reminder."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(os.environ.get('XDG_STATE_HOME', str(Path.home()/'.local/state')))/'coding-health-guard'
DEFAULTS = dict(work=60, countdown=120, short=10, long=20, every=3, snooze=5, reminders=[8,10], hard=False)

def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2))
    tmp.chmod(0o600)
    tmp.replace(path)

def read(path, default):
    try:
        data=json.loads(path.read_text())
        return data if isinstance(data,dict) else default.copy()
    except (OSError, ValueError):
        return default.copy()

class Timer:
    def __init__(self, directory=ROOT, now=time.time):
        self.root=directory; self.now=now
        self.config=DEFAULTS.copy(); raw=read(directory/'config.json', {})
        for key in ('work','countdown','short','long','every','snooze'):
            value=raw.get(key)
            if isinstance(value,int) and not isinstance(value,bool) and 1<=value<=1440: self.config[key]=value
        if isinstance(raw.get('hard'),bool): self.config['hard']=raw['hard']
        hours=raw.get('reminders')
        if isinstance(hours,list) and hours and all(isinstance(h,(int,float)) and not isinstance(h,bool) and 0<h<=24 for h in hours): self.config['reminders']=hours
        self.s=dict(phase='idle', deadline=0, sessions=0, day='', total=0, last=now(), warned=[])
        self.s.update(read(directory/'state.json', {}))
        self.s.setdefault('warned', [])
        if not all(isinstance(self.s.get(k),(int,float)) and self.s[k]>=0 for k in ('deadline','sessions','total','last')) or not isinstance(self.s.get('warned'),list):
            self.s=dict(phase='idle',deadline=0,sessions=0,day='',total=0,last=now(),warned=[])
        if self.s.get('phase') not in ('idle','work','countdown','break'): self.s['phase']='idle'
        self.persist()
    def persist(self): save(self.root/'state.json', self.s)
    def begin(self):
        self.s.update(phase='work', deadline=self.now()+self.config['work']*60, last=self.now()); self.persist()
    def rest(self):
        self.s['sessions']+=1
        duration=self.config['long'] if self.s['sessions']%self.config['every']==0 else self.config['short']
        self.s.update(phase='break', deadline=self.now()+duration*60); self.persist()
    def tick(self):
        now=self.now(); day=time.strftime('%Y-%m-%d', time.localtime(now))
        if self.s['day']!=day: self.s.update(day=day,total=0,warned=[])
        if self.s['phase'] in ('work','countdown'):
            # Count observed running time only; logout/suspend gaps do not inflate daily use.
            self.s['total']+=max(0,min(2,now-self.s['last']))
        self.s['last']=now
        event=None
        if self.s['phase']!='idle' and now>=self.s['deadline']:
            if self.s['phase']=='work':
                self.s.update(phase='countdown',deadline=now+self.config['countdown']); event='countdown'
            elif self.s['phase']=='countdown': self.rest(); event='break'
            else: self.s.update(phase='idle',deadline=0); event='finished'
        self.persist(); return event
    def snooze(self):
        if self.config['hard']: return False
        self.s.update(phase='work',deadline=self.now()+self.config['snooze']*60); self.persist(); return True

def lock_session():
    commands=[['gdbus','call','--session','--dest','org.gnome.ScreenSaver','--object-path','/org/gnome/ScreenSaver','--method','org.gnome.ScreenSaver.Lock']]
    sid=os.environ.get('XDG_SESSION_ID')
    if sid: commands.append(['loginctl','lock-session',sid])
    for cmd in commands:
        try:
            if subprocess.run(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=4).returncode==0: return True
        except (OSError,subprocess.TimeoutExpired): pass
    return False

def run_gui(timer):
    import gi
    gi.require_version('Gtk','3.0')
    from gi.repository import Gtk, GLib, Gdk
    class UI:
        def __init__(self):
            self.t=timer; self.overlays=[]; self.tray=None; self.lock_error=False
            self.w=Gtk.Window(title='Coding Health Guard'); self.w.set_default_size(520,420)
            self.w.connect('delete-event',self.close)
            box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12); box.set_border_width(24); self.w.add(box)
            title=Gtk.Label(); title.set_markup('<big><b>Coding Health Guard</b></big>'); box.pack_start(title,False,False,0)
            self.label=Gtk.Label(label=''); box.pack_start(self.label,True,True,0)
            self.question=Gtk.Label(label='Baru mulai coding? Apakah Anda sudah istirahat?'); box.pack_start(self.question,False,False,0)
            self.buttons={}
            for text,fn in [('Mulai — sudah istirahat',self.start),('Belum istirahat',self.rest),('Lanjut sesi',self.resume),('Tunda',self.snooze),('Lewati istirahat',self.skip),('Pengaturan',self.settings),('Sembunyikan',lambda:self.w.hide())]:
                b=Gtk.Button(label=text); b.connect('clicked',lambda _,f=fn:f()); box.pack_start(b,False,False,0); self.buttons[text]=b
            self.setup_tray(); self.w.show_all()
            GLib.timeout_add_seconds(1,self.tick); self.tick()
        def setup_tray(self):
            try:
                gi.require_version('AyatanaAppIndicator3','0.1')
                from gi.repository import AyatanaAppIndicator3 as A
                self.tray=A.Indicator.new('coding-health-guard','appointment-soon',A.IndicatorCategory.APPLICATION_STATUS)
                menu=Gtk.Menu()
                item=Gtk.MenuItem(label='Buka Coding Health Guard'); item.connect('activate',lambda _:self.w.present()); menu.append(item)
                menu.show_all(); self.tray.set_menu(menu); self.tray.set_status(A.IndicatorStatus.ACTIVE)
            except (ImportError,ValueError): pass
        def close(self,*_):
            self.w.hide(); return True
        def start(self):
            if self.t.config['hard'] and self.t.s['phase']!='idle': return
            self.t.begin(); self.tick()
        def rest(self):
            if self.t.s['phase']=='break': return
            self.t.rest(); self.enter_rest()
        def resume(self): self.w.hide()
        def snooze(self): self.t.snooze(); self.tick()
        def skip(self):
            if not self.t.config['hard']: self.t.begin(); self.tick()
        def enter_rest(self):
            self.w.present()
            if self.t.config['hard']:
                self.make_overlays()
                self.lock_error=not lock_session()
        def make_overlays(self):
            if self.overlays: return
            display=Gdk.Display.get_default()
            for i in range(display.get_n_monitors()):
                w=Gtk.Window(title='Waktunya istirahat'); w.set_decorated(False); w.set_keep_above(True)
                w.connect('delete-event',lambda *_:True)
                box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=24); box.set_border_width(48); w.add(box)
                label=Gtk.Label(); box.pack_start(label,True,True,0)
                hint=Gtk.Label(label='Pemulihan darurat: tahan Ctrl+Shift+Esc selama 5 detik.'); box.pack_start(hint,False,False,0)
                w.connect('key-press-event',self.emergency_key); w.connect('key-release-event',self.emergency_release)
                w.connect('focus-out-event',self.emergency_release)
                w.show_all(); w.fullscreen_on_monitor(w.get_screen(),i); self.overlays.append((w,label))
        def emergency_key(self,w,e):
            mask=Gdk.ModifierType.CONTROL_MASK|Gdk.ModifierType.SHIFT_MASK
            if e.keyval==Gdk.KEY_Escape and e.state&mask==mask:
                if not getattr(self,'emergency_at',None): self.emergency_at=time.monotonic()
            return False
        def emergency_release(self,*_): self.emergency_at=None; return False
        def settings(self):
            if self.t.config['hard'] and self.t.s['phase']!='idle': return
            d=Gtk.Dialog(title='Pengaturan (berlaku sesi berikutnya)',transient_for=self.w)
            d.add_buttons('Batal',Gtk.ResponseType.CANCEL,'Simpan',Gtk.ResponseType.OK)
            box=d.get_content_area(); fields={}
            labels=dict(work='Coding (menit)',countdown='Hitung mundur (detik)',short='Istirahat (menit)',long='Istirahat panjang (menit)',every='Istirahat panjang setiap sesi',snooze='Tunda (menit)')
            for key,label in labels.items():
                row=Gtk.Box(spacing=12); row.pack_start(Gtk.Label(label=label),True,True,0)
                spin=Gtk.SpinButton.new_with_range(1,1440,1); spin.set_value(self.t.config[key]); row.add(spin); box.add(row); fields[key]=spin
            rem=Gtk.Entry(); rem.set_text(','.join(map(str,self.t.config['reminders']))); box.add(Gtk.Label(label='Pengingat jam coding harian (pisahkan koma)')); box.add(rem)
            hard=Gtk.CheckButton(label='Mode keras — tanpa lewati/tunda; kunci Ubuntu'); hard.set_active(self.t.config['hard']); box.add(hard)
            d.show_all()
            if d.run()==Gtk.ResponseType.OK:
                try:
                    hours=[float(x.strip()) for x in rem.get_text().split(',')]
                    if not hours or any(not 0<h<=24 for h in hours): raise ValueError()
                    self.t.config.update({k:v.get_value_as_int() for k,v in fields.items()}); self.t.config.update(hard=hard.get_active(),reminders=hours)
                    save(self.t.root/'config.json',self.t.config)
                except ValueError: self.message('Pengingat tidak valid. Gunakan angka lebih dari 0 hingga 24. Perubahan dibatalkan.')
            d.destroy(); self.tick()
        def message(self,text):
            d=Gtk.MessageDialog(transient_for=self.w,flags=0,message_type=Gtk.MessageType.INFO,buttons=Gtk.ButtonsType.OK,text=text); d.run(); d.destroy()
        def tick(self):
            if (self.t.root/'show').exists():
                (self.t.root/'show').unlink(missing_ok=True); self.w.show_all(); self.w.present()
            if (self.t.root/'recover').exists():
                (self.t.root/'recover').unlink(missing_ok=True); self.t.s.update(phase='idle',deadline=0); self.t.persist(); Gtk.main_quit(); return False
            event=self.t.tick(); phase=self.t.s['phase']; hard=self.t.config['hard']
            if event=='break': self.enter_rest()
            if phase=='break' and hard: self.make_overlays()
            if phase!='break':
                for w,_ in self.overlays: w.destroy()
                self.overlays=[]
            if event in ('countdown','finished'): self.w.present()
            if getattr(self,'emergency_at',None) and time.monotonic()-self.emergency_at>=5:
                self.t.s.update(phase='idle',deadline=0); self.t.persist(); Gtk.main_quit(); return False
            remaining=max(0,int(self.t.s['deadline']-time.time()))
            text={'idle':'Siap memulai sesi', 'work':'Waktu coding', 'countdown':'Simpan pekerjaan — istirahat segera', 'break':'Istirahat: berdiri dan alihkan pandangan'}[phase]
            status=f'{text}\n{remaining//60:02d}:{remaining%60:02d} • Sesi selesai: {self.t.s["sessions"]}\nCoding hari ini: {self.t.s["total"]/3600:.1f} jam'
            if self.lock_error: status+='\nPermintaan kunci gagal. Kunci manual dengan Super+L.'
            self.label.set_text(status)
            for _,label in self.overlays: label.set_text(status)
            active=phase!='idle'
            self.buttons['Mulai — sudah istirahat'].set_sensitive(not(hard and active))
            self.buttons['Pengaturan'].set_sensitive(not(hard and active))
            self.buttons['Belum istirahat'].set_sensitive(phase!='break')
            self.buttons['Lanjut sesi'].set_sensitive(active)
            for name in ('Tunda','Lewati istirahat'): self.buttons[name].set_visible(not hard and phase in ('countdown','break'))
            for hour in self.t.config['reminders']:
                if self.t.s['total']>=hour*3600 and hour not in self.t.s['warned']:
                    self.t.s['warned'].append(hour); self.t.persist(); self.message(f'Anda sudah coding {hour:g} jam hari ini. Pertimbangkan mengakhiri pekerjaan dan beristirahat.')
            return True
    UI(); Gtk.main()

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--recover',action='store_true'); args=parser.parse_args()
    ROOT.mkdir(parents=True,exist_ok=True)
    if args.recover:
        # Cooperatively exit the GUI before resetting its saved state.
        (ROOT/'recover').touch()
        print('Pemulihan diminta. Tunggu 3 detik sebelum membuka aplikasi kembali.'); return
    handle=(ROOT/'instance.lock').open('w')
    try: fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError: (ROOT/'show').touch(); print('Membuka aplikasi yang sudah berjalan.'); return
    recovered=(ROOT/'recover').exists()
    if recovered: (ROOT/'recover').unlink()
    timer=Timer()
    if recovered: timer.s.update(phase='idle',deadline=0); timer.persist()
    try: run_gui(timer)
    except (ImportError,ValueError) as e: raise SystemExit('GTK belum tersedia. Jalankan installer. '+str(e))
if __name__=='__main__': main()
