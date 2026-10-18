import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from guard import Timer, read, lock_session

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.now=100000; self.root=Path(self.tmp.name)
        self.t=Timer(self.root,lambda:self.now)
    def test_bad_config(self):
        (self.root/'config.json').write_text('{"work": 0, "every": 0, "hard": "yes", "reminders": [99]}')
        t=Timer(self.root); self.assertEqual(t.config['work'],60); self.assertEqual(t.config['every'],3); self.assertFalse(t.config['hard'])
    def test_partial_state(self):
        (self.root/'state.json').write_text('{"deadline": 1}')
        Timer(self.root).tick()
    def test_cycle(self):
        self.t.begin(); self.now+=3600
        self.assertEqual(self.t.tick(),'countdown')
        self.now+=119; self.assertIsNone(self.t.tick())
        self.now+=1; self.assertEqual(self.t.tick(),'break')
        self.assertEqual(self.t.s['deadline'],self.now+600)
        self.now+=600; self.assertEqual(self.t.tick(),'finished')
    def test_long_break(self):
        for _ in range(3): self.t.begin(); self.t.rest()
        self.assertEqual(self.t.s['deadline'],self.now+1200)
    def test_hard_disallows_snooze(self):
        self.t.config['hard']=True; self.t.rest(); state=self.t.s.copy()
        self.assertFalse(self.t.snooze()); self.assertEqual(state,self.t.s)
    def test_snooze(self):
        self.t.rest(); self.assertTrue(self.t.snooze())
        self.assertEqual(self.t.s['deadline'],self.now+300)
    def test_persistence(self):
        self.t.rest(); t=Timer(self.root,lambda:self.now)
        self.assertEqual(t.s,self.t.s)
        self.now+=600; self.assertEqual(t.tick(),'finished')
    def test_corrupt_state(self):
        (self.root/'state.json').write_text('{')
        self.assertEqual(Timer(self.root).s['phase'],'idle')
    def test_logout_gap_not_counted(self):
        self.t.begin(); self.now+=30000; self.t.tick()
        self.assertLessEqual(self.t.s['total'],2)
    @patch('guard.subprocess.run')
    def test_lock_failure(self,run):
        run.return_value.returncode=1
        self.assertFalse(lock_session())
    @patch('guard.subprocess.run')
    def test_lock_success(self,run):
        run.return_value.returncode=0
        self.assertTrue(lock_session())
if __name__=='__main__': unittest.main()
