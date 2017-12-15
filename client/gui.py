#! /usr/bin/env python3
"""Register tkinter classes with thread_box for immediate usage.

This module clones several classes from the tkinter library for use with
threads. Instances from these new classes should run on whatever thread
the root was created on. Child classes inherit the parent's safety."""

__author__ = 'Stephen "Zero" Chappell ' \
             '<stephen.paul.chappell@atlantis-zero.net>'
__date__ = '15 December 2017'
__version__ = 1, 0, 1
__all__ = [
    'BooleanVar',
    'DoubleVar',
    'IntVar',
    'StringVar',
    'BitmapImage',
    'Canvas',
    'ListBox',
    'Menu',
    'Message',
    'PhotoImage',
    'SpinBox',
    'Text',
    'Tk',
    'TopLevel',
    'ComboBox',
    'LabeledScale',
    'Notebook',
    'ProgressBar',
    'Separator',
    'SizeGrip',
    'Style',
    'TreeView',
    'Button',
    'CheckButton',
    'Entry',
    'Frame',
    'Label',
    'LabelFrame',
    'MenuButton',
    'OptionMenu',
    'PanedWindow',
    'RadioButton',
    'Scale',
    'ScrollBar',
    'Directory',
    'Font',
    'MessageBox',
    'Open',
    'ScrolledText'
]

import _tkinter
import time
import tkinter
import tkinter.filedialog
import tkinter.font
import tkinter.messagebox
import tkinter.scrolledtext
import tkinter.ttk

import client.thread_box as thread_box

tkinter.NoDefaultRoot()


@thread_box.MetaBox.thread
def mainloop(self):
    """Create a synthetic main loop so that threads can still run."""
    while True:
        try:
            self.update()
        except tkinter.TclError:
            break
        else:
            time.sleep(_tkinter.getbusywaitinterval() / 1000)


# Prime MetaBox with a Misc class and new mainloop method.
thread_box.MetaBox.clone(tkinter.Misc, {'mainloop': mainloop})

# Clone tkinter's variable holders in case they are needed.
BooleanVar = thread_box.MetaBox.clone(tkinter.BooleanVar)
DoubleVar = thread_box.MetaBox.clone(tkinter.DoubleVar)
IntVar = thread_box.MetaBox.clone(tkinter.IntVar)
StringVar = thread_box.MetaBox.clone(tkinter.StringVar)

# Clone tkinter classes that do not have a ttk counterpart.
BitmapImage = thread_box.MetaBox.clone(tkinter.BitmapImage)
Canvas = thread_box.MetaBox.clone(tkinter.Canvas)
ListBox = thread_box.MetaBox.clone(tkinter.Listbox)
Menu = thread_box.MetaBox.clone(tkinter.Menu)
Message = thread_box.MetaBox.clone(tkinter.Message)
PhotoImage = thread_box.MetaBox.clone(tkinter.PhotoImage)
SpinBox = thread_box.MetaBox.clone(tkinter.Spinbox)
Text = thread_box.MetaBox.clone(tkinter.Text)
Tk = thread_box.MetaBox.clone(tkinter.Tk)
TopLevel = thread_box.MetaBox.clone(tkinter.Toplevel)

# Clone tkinter classes that have a ttk counterpart and add name prefix.
_Button = thread_box.MetaBox.clone(tkinter.Button)
_CheckButton = thread_box.MetaBox.clone(tkinter.Checkbutton)
_Entry = thread_box.MetaBox.clone(tkinter.Entry)
_Frame = thread_box.MetaBox.clone(tkinter.Frame)
_Label = thread_box.MetaBox.clone(tkinter.Label)
_LabelFrame = thread_box.MetaBox.clone(tkinter.LabelFrame)
_MenuButton = thread_box.MetaBox.clone(tkinter.Menubutton)
_OptionMenu = thread_box.MetaBox.clone(tkinter.OptionMenu)
_PanedWindow = thread_box.MetaBox.clone(tkinter.PanedWindow)
_RadioButton = thread_box.MetaBox.clone(tkinter.Radiobutton)
_Scale = thread_box.MetaBox.clone(tkinter.Scale)
_ScrollBar = thread_box.MetaBox.clone(tkinter.Scrollbar)

# Clone ttk classes that do not have a tkinter counterpart.
ComboBox = thread_box.MetaBox.clone(tkinter.ttk.Combobox)
LabeledScale = thread_box.MetaBox.clone(tkinter.ttk.LabeledScale)
Notebook = thread_box.MetaBox.clone(tkinter.ttk.Notebook)
ProgressBar = thread_box.MetaBox.clone(tkinter.ttk.Progressbar)
Separator = thread_box.MetaBox.clone(tkinter.ttk.Separator)
SizeGrip = thread_box.MetaBox.clone(tkinter.ttk.Sizegrip)
Style = thread_box.MetaBox.clone(tkinter.ttk.Style)
TreeView = thread_box.MetaBox.clone(tkinter.ttk.Treeview)

# Clone ttk classes that have a tkinter counterpart and keep original name.
Button = thread_box.MetaBox.clone(tkinter.ttk.Button)
CheckButton = thread_box.MetaBox.clone(tkinter.ttk.Checkbutton)
Entry = thread_box.MetaBox.clone(tkinter.ttk.Entry)
Frame = thread_box.MetaBox.clone(tkinter.ttk.Frame)
Label = thread_box.MetaBox.clone(tkinter.ttk.Label)
LabelFrame = thread_box.MetaBox.clone(tkinter.ttk.Labelframe)
MenuButton = thread_box.MetaBox.clone(tkinter.ttk.Menubutton)
OptionMenu = thread_box.MetaBox.clone(tkinter.ttk.OptionMenu)
PanedWindow = thread_box.MetaBox.clone(tkinter.ttk.Panedwindow)
RadioButton = thread_box.MetaBox.clone(tkinter.ttk.Radiobutton)
Scale = thread_box.MetaBox.clone(tkinter.ttk.Scale)
ScrollBar = thread_box.MetaBox.clone(tkinter.ttk.Scrollbar)

# Clone other GUI utility classes for use in applications.
Directory = thread_box.MetaBox.clone(tkinter.filedialog.Directory)
Font = thread_box.MetaBox.clone(tkinter.font.Font)
MessageBox = thread_box.MetaBox.clone(tkinter.messagebox.Message)
Open = thread_box.MetaBox.clone(tkinter.filedialog.Open)
ScrolledText = thread_box.MetaBox.clone(tkinter.scrolledtext.ScrolledText)
