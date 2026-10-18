"""Run only on an isolated development display; native lock is mocked."""
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk, GLib
import guard

class DesktopTest(unittest.TestCase):
    def test_work_break_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            timer=guard.Timer(Path(directory)); failures=[]; stage=[0]
            def buttons():
                result={}
                def walk(widget):
                    if isinstance(widget,Gtk.Button): result[widget.get_label()]=widget
                    if isinstance(widget,Gtk.Container):
                        for child in widget.get_children(): walk(child)
                for w in Gtk.Window.list_toplevels(): walk(w)
                return result
            def check():
                try:
                    b=buttons()
                    if stage[0]==0:
                        self.assertIn('Lanjut sesi',b)
                        b['Pengaturan'].clicked()
                        dialogs=[w for w in Gtk.Window.list_toplevels() if isinstance(w,Gtk.Dialog)]
                        self.assertTrue(dialogs)
                        dialogs[0].response(Gtk.ResponseType.CANCEL)
                        timer.s.update(day=time.strftime('%Y-%m-%d'),total=8*3600)
                        b['Mulai — sudah istirahat'].clicked(); self.assertEqual(timer.s['phase'],'work')
                        self.assertTrue(any(isinstance(w,Gtk.MessageDialog) for w in Gtk.Window.list_toplevels()))
                        timer.s['deadline']=0
                    elif stage[0]==1:
                        self.assertEqual(timer.s['phase'],'countdown'); self.assertTrue(b['Tunda'].get_visible())
                        b['Tunda'].clicked(); self.assertEqual(timer.s['phase'],'work')
                        timer.config['hard']=True; timer.s['deadline']=0
                    elif stage[0]==2:
                        self.assertEqual(timer.s['phase'],'countdown'); self.assertFalse(b['Tunda'].get_visible())
                        self.assertFalse(b['Pengaturan'].get_sensitive()); timer.s['deadline']=0
                    elif stage[0]==3:
                        self.assertEqual(timer.s['phase'],'break')
                        overlays=[w for w in Gtk.Window.list_toplevels() if w.get_title()=='Waktunya istirahat']
                        self.assertTrue(overlays)
                        self.assertTrue(overlays[0].get_child().get_can_focus())
                        self.assertEqual(overlays[0].get_focus(),overlays[0].get_child())
                        (timer.root/'recover').touch()
                    else: return False
                    stage[0]+=1
                    return True
                except Exception as exc:
                    failures.append(exc); Gtk.main_quit(); return False
            GLib.timeout_add(1600,check)
            GLib.timeout_add_seconds(15,lambda: (Gtk.main_quit(),False)[1])
            with patch('guard.lock_session',return_value=True) as lock:
                guard.run_gui(timer)
                self.assertEqual(lock.call_count,1)
            if failures: raise failures[0]
            self.assertEqual(timer.s['phase'],'idle')
            for w in Gtk.Window.list_toplevels(): w.destroy()

if __name__=='__main__': unittest.main()
