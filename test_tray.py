import unittest
from gi.repository import GLib
from tray import Tray

class Invocation:
    def return_value(self,value):self.result=value
    def return_dbus_error(self,name,message):self.error=name

class TrayMenuTests(unittest.TestCase):
    def setUp(self):
        self.opened=[]
        self.tray=Tray.__new__(Tray);self.tray.activate=lambda:self.opened.append(True)
    def call(self,method,parameters):
        invocation=Invocation()
        self.tray.menu_method(None,None,None,None,method,parameters,invocation)
        return invocation
    def test_wire_layout_has_open_action(self):
        reply=self.call('GetLayout',GLib.Variant('(iias)',(0,-1,[]))).result
        revision,layout=reply.unpack()
        self.assertEqual(revision,1)
        self.assertEqual(layout[2][0][1]['label'],'Buka Coding Health Guard')
        self.assertTrue(layout[2][0][1]['enabled'])
    def test_menu_click_opens_window(self):
        self.call('Event',GLib.Variant('(isvu)',(1,'clicked',GLib.Variant('i',0),0)))
        self.assertEqual(self.opened,[True])
    def test_unknown_property_is_explicit_error(self):
        reply=self.call('GetProperty',GLib.Variant('(is)',(1,'missing')))
        self.assertEqual(reply.error,'com.canonical.dbusmenu.Error.UnknownProperty')
if __name__=='__main__':unittest.main()
