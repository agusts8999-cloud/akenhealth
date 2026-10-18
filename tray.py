"""StatusNotifierItem + DBusMenu without GtkStatusIcon/XEmbed fallback.

GNOME disables its tray watcher while locked. Keep exporting the item and
register again when the watcher returns; never create an X11 tray on Wayland.
"""
from gi.repository import Gio, GLib

ITEM_XML='''<node><interface name="org.kde.StatusNotifierItem">
<method name="Activate"><arg type="i" direction="in"/><arg type="i" direction="in"/></method>
<method name="SecondaryActivate"><arg type="i" direction="in"/><arg type="i" direction="in"/></method>
<method name="ContextMenu"><arg type="i" direction="in"/><arg type="i" direction="in"/></method>
<method name="Scroll"><arg type="i" direction="in"/><arg type="s" direction="in"/></method>
<property name="Category" type="s" access="read"/>
<property name="Id" type="s" access="read"/>
<property name="Title" type="s" access="read"/>
<property name="Status" type="s" access="read"/>
<property name="WindowId" type="u" access="read"/>
<property name="IconName" type="s" access="read"/>
<property name="IconPixmap" type="a(iiay)" access="read"/>
<property name="OverlayIconName" type="s" access="read"/>
<property name="OverlayIconPixmap" type="a(iiay)" access="read"/>
<property name="AttentionIconName" type="s" access="read"/>
<property name="AttentionIconPixmap" type="a(iiay)" access="read"/>
<property name="AttentionMovieName" type="s" access="read"/>
<property name="IconThemePath" type="s" access="read"/>
<property name="ToolTip" type="(sa(iiay)ss)" access="read"/>
<property name="ItemIsMenu" type="b" access="read"/>
<property name="Menu" type="o" access="read"/>
<property name="DesktopEntry" type="s" access="read"/>
<signal name="NewIcon"/><signal name="NewToolTip"/>
<signal name="NewStatus"><arg type="s"/></signal>
</interface></node>'''
MENU_XML='''<node><interface name="com.canonical.dbusmenu">
<method name="GetLayout"><arg type="i" direction="in"/><arg type="i" direction="in"/><arg type="as" direction="in"/><arg type="u" direction="out"/><arg type="(ia{sv}av)" direction="out"/></method>
<method name="GetGroupProperties"><arg type="ai" direction="in"/><arg type="as" direction="in"/><arg type="a(ia{sv})" direction="out"/></method>
<method name="GetProperty"><arg type="i" direction="in"/><arg type="s" direction="in"/><arg type="v" direction="out"/></method>
<method name="Event"><arg type="i" direction="in"/><arg type="s" direction="in"/><arg type="v" direction="in"/><arg type="u" direction="in"/></method>
<method name="EventGroup"><arg type="a(isvu)" direction="in"/><arg type="ai" direction="out"/></method>
<method name="AboutToShow"><arg type="i" direction="in"/><arg type="b" direction="out"/></method>
<method name="AboutToShowGroup"><arg type="ai" direction="in"/><arg type="ai" direction="out"/><arg type="ai" direction="out"/></method>
<property name="Version" type="u" access="read"/>
<property name="TextDirection" type="s" access="read"/>
<property name="Status" type="s" access="read"/>
<property name="IconThemePath" type="as" access="read"/>
<signal name="LayoutUpdated"><arg type="u"/><arg type="i"/></signal>
</interface></node>'''

class Tray:
    def __init__(self, activate):
        self.activate=activate
        self.bus=Gio.bus_get_sync(Gio.BusType.SESSION,None)
        self.item_info=Gio.DBusNodeInfo.new_for_xml(ITEM_XML)
        self.menu_info=Gio.DBusNodeInfo.new_for_xml(MENU_XML)
        self.registrations=[
            self.bus.register_object('/StatusNotifierItem',self.item_info.interfaces[0],self.item_method,self.item_property,None),
            self.bus.register_object('/Menu',self.menu_info.interfaces[0],self.menu_method,self.menu_property,None)]
        self.watch=Gio.bus_watch_name_on_connection(self.bus,'org.kde.StatusNotifierWatcher',Gio.BusNameWatcherFlags.NONE,self.appeared,lambda *_:None)
    def appeared(self,connection,name,owner):
        connection.call(name,'/StatusNotifierWatcher','org.kde.StatusNotifierWatcher','RegisterStatusNotifierItem',GLib.Variant('(s)',('/StatusNotifierItem',)),None,Gio.DBusCallFlags.NONE,2000,None,self.registered)
    def registered(self,connection,result):
        try:connection.call_finish(result)
        except GLib.Error:pass  # No tray is a supported desktop configuration.
    def item_method(self,connection,sender,path,interface,method,params,invocation):
        if method in ('Activate','SecondaryActivate','ContextMenu'):self.activate()
        invocation.return_value(GLib.Variant('()',()))
    def item_property(self,connection,sender,path,interface,name):
        strings=dict(Category='ApplicationStatus',Id='coding-health-guard',Title='Coding Health Guard',Status='Active',IconName='appointment-soon',OverlayIconName='',AttentionIconName='',AttentionMovieName='',IconThemePath='',DesktopEntry='coding-health-guard')
        if name in strings:return GLib.Variant('s',strings[name])
        if name.endswith('Pixmap'):return GLib.Variant('a(iiay)',[])
        if name=='WindowId':return GLib.Variant('u',0)
        if name=='ItemIsMenu':return GLib.Variant('b',True)
        if name=='Menu':return GLib.Variant('o','/Menu')
        if name=='ToolTip':return GLib.Variant('(sa(iiay)ss)',('appointment-soon',[],'Coding Health Guard','Pengingat istirahat coding'))
    def menu_properties(self,item):
        if item==0:return {'children-display':GLib.Variant('s','submenu')}
        if item==1:return {'label':GLib.Variant('s','Buka Coding Health Guard'),'enabled':GLib.Variant('b',True),'visible':GLib.Variant('b',True)}
        return {}
    def menu_property(self,connection,sender,path,interface,name):
        if name=='Version':return GLib.Variant('u',3)
        if name=='IconThemePath':return GLib.Variant('as',[])
        return GLib.Variant('s','ltr' if name=='TextDirection' else 'normal')
    def menu_method(self,connection,sender,path,interface,method,params,invocation):
        values=params.unpack()
        if method=='GetLayout':
            parent=values[0]
            children=[GLib.Variant('(ia{sv}av)',(1,self.menu_properties(1),[]))] if parent==0 and values[1]!=0 else []
            result=GLib.Variant('(u(ia{sv}av))',(1,(parent,self.menu_properties(parent),children)))
        elif method=='GetGroupProperties':
            ids=values[0] or [0,1]
            result=GLib.Variant('(a(ia{sv}))',([(item,self.menu_properties(item)) for item in ids if item in (0,1)],))
        elif method=='GetProperty':
            value=self.menu_properties(values[0]).get(values[1])
            if value is None:
                invocation.return_dbus_error('com.canonical.dbusmenu.Error.UnknownProperty','Unknown property');return
            result=GLib.Variant('(v)',(value,))
        elif method in ('Event','EventGroup'):
            events=[values] if method=='Event' else values[0]
            for item,event,*_ in events:
                if item==1 and event=='clicked':self.activate()
            result=GLib.Variant('()',()) if method=='Event' else GLib.Variant('(ai)',([],))
        elif method=='AboutToShow':result=GLib.Variant('(b)',(False,))
        elif method=='AboutToShowGroup':result=GLib.Variant('(aiai)',([],[]))
        else:
            invocation.return_dbus_error('org.freedesktop.DBus.Error.UnknownMethod','Unknown method');return
        invocation.return_value(result)
