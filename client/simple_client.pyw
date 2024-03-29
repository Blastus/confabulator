#! /usr/bin/env python3
"""Provide a GUI for easy interactions with Confabulator servers.

This program is an example of a first attempt at implementing a client
for interacting with a Confabulator server through purely graphical means."""

__author__ = 'Stephen "Zero" Chappell ' \
             '<stephen.paul.chappell@atlantis-zero.net>'
__date__ = '14 December 2017'
__version__ = 1, 0, 1
__all__ = [
    'SimpleClient',
    'start_thread',
    'log_errors',
    'ConnectionDialog',
    'ConnectionStatus'
]

import _thread
import logging
import pathlib
import socket
import sys
import traceback
from tkinter.constants import *
from tkinter.messagebox import WARNING, OK

sys.path.append(str(pathlib.PurePath(sys.argv[0]).parents[1]))

# noinspection PyPep8
from client.safe_tkinter import *


class SimpleClient(Frame):
    """SimpleClient(master, **kw) -> SimpleClient instance"""

    @classmethod
    def main(cls):
        """Create a GUI root and demonstrate the SimpleClient widget."""
        root = Tk()
        root.title('Chat Client')
        root.minsize(675, 450)
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)
        root.bind_all('<Control-Key-a>', cls.handle_control_a)
        frame = cls(root)
        frame.grid(sticky=NSEW)
        root.mainloop()

    @staticmethod
    def handle_control_a(event):
        """Process Ctrl-A commands by widget type."""
        widget = event.widget
        if isinstance(widget, Text):
            widget.tag_add(SEL, 1.0, END + '-1c')
            return 'break'
        if isinstance(widget, Entry):
            widget.selection_range(0, END)
            return 'break'

    def __init__(self, master, **kw):
        """Initialize the SimpleClient instance with the widgets it uses."""
        super().__init__(master, **kw)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        # Build Widgets
        self.output_area = ScrolledText(self, width=25, height=4, wrap=WORD)
        self.input_area = Entry(self)
        self.corner = SizeGrip(self)
        # Place Widgets
        self.output_area.grid(row=0, column=0, columnspan=2, sticky=NSEW)
        self.input_area.grid(row=1, column=0, sticky=EW)
        self.corner.grid(row=1, column=1, sticky=SE)
        # Setup Widgets
        self.output_area['state'] = DISABLED
        self.input_area.bind('<Return>', self.send)
        self.after_handle = self.after_idle(self.connect)
        self.connection = None

    def destroy(self):
        """Destruct the SimpleClient window."""
        self.after_cancel(self.after_handle)
        super().destroy()

    def connect(self):
        """Try connecting to a server to begin chatting."""
        # noinspection PyTypeChecker
        self.connection = ConnectionDialog(self, 'Chat Client').connection
        if self.connection is None:
            self._root().destroy()
        else:
            self.connection.setblocking(False)
            self.after_handle = self.after_idle(self.update)

    def send(self, event):
        """Send a message across the connection from the given widget."""
        try:
            self.connection.sendall(event.widget.get().encode() + b'\r\n')
        except ConnectionAbortedError:
            pass
        finally:
            event.widget.delete(0, END)

    def update(self):
        """Update the output area with any incoming messages."""
        self.output_area['state'] = NORMAL
        try:
            message = self.connection.recv(1 << 12)
        except socket.error:
            pass
        else:
            self.output_area.insert(END, message.decode())
            self.output_area.see(END)
        finally:
            self.output_area['state'] = DISABLED
            self.after_handle = self.after(100, self.update)


def start_thread(entry_point, *args, **kwargs):
    """Start a new thread of execution while logging any errors."""
    _thread.start_new_thread(log_errors, (entry_point, args, kwargs))


def log_errors(entry_point, args=(), kwargs=None):
    """Execute a function with its arguments and log any exceptions."""
    if kwargs is None:
        kwargs = {}
    # noinspection PyPep8,PyBroadException
    try:
        entry_point(*args, **kwargs)
    except SystemExit:
        pass
    except:
        destination = pathlib.Path(sys.argv[0]).with_suffix('.log')
        logging.basicConfig(filename=destination)
        logging.error(traceback.format_exc())


class Dialog(TopLevel):
    """Dialog(parent, title=None) -> Dialog instance"""

    def __init__(self, parent, title=None):
        """Initialize a Dialog window that takes focus away from the parent."""
        super().__init__(parent)
        self.withdraw()
        if parent.winfo_viewable():
            self.transient(parent)
        if title:
            self.title(title)
        self.parent = parent
        self.result = None
        body = Frame(self)
        self.initial_focus = self.body(body)
        body.grid(sticky=NSEW, padx=5, pady=5)
        self.buttonbox()
        if not self.initial_focus:
            self.initial_focus = self
        self.protocol('WM_DELETE_WINDOW', self.cancel)
        if self.parent is not None:
            x = parent.winfo_rootx() + 50
            y = parent.winfo_rooty() + 50
            self.geometry(f'+{x}+{y}')
        self.deiconify()
        self.initial_focus.focus_set()
        try:
            self.wait_visibility()
        except tkinter.TclError:
            pass
        else:
            self.grab_set()
            self.wait_window(self)

    def destroy(self):
        """Destruct the Dialog window."""
        self.initial_focus = None
        super().destroy()

    def body(self, master):
        """Create the body of this Dialog window."""
        pass

    def buttonbox(self):
        """Create the standard buttons and Dialog bindings."""
        box = Frame(self)
        w = Button(box, text='OK', width=10, command=self.ok, default=ACTIVE)
        w.grid(row=0, column=0, padx=5, pady=5)
        w = Button(box, text='Cancel', width=10, command=self.cancel)
        w.grid(row=0, column=1, padx=5, pady=5)
        self.bind('<Return>', self.ok)
        self.bind('<Escape>', self.cancel)
        box.grid()

    # noinspection PyUnusedLocal
    def ok(self, event=None):
        """Validate and apply the changes made by this Dialog."""
        if not self.validate():
            self.initial_focus.focus_set()
            return
        self.withdraw()
        self.update_idletasks()
        try:
            self.apply()
        finally:
            self.cancel()

    # noinspection PyUnusedLocal
    def cancel(self, event=None):
        """Close the Dialog window and return to its parent."""
        if self.parent is not None:
            self.parent.focus_set()
        self.destroy()

    def validate(self):
        """Verify that the Dialog is in a valid state."""
        return True

    def apply(self):
        """Make any changes the Dialog wishes to accomplish."""
        pass


class ConnectionDialog(Dialog):
    """ConnectionDialog(parent, title=None) -> ConnectionDialog instance"""

    def __init__(self, parent, title=None):
        self.connection = self.prompt = self.address = None
        super().__init__(parent, title)

    def body(self, master):
        """Customize the Dialog window with some custom widgets."""
        self.connection = None
        self.resizable(False, False)
        # Build Widgets
        self.prompt = Label(master, text='Enter server IP address:')
        self.address = Entry(master)
        # Place Widgets
        self.prompt.grid(sticky=W, padx=30, pady=2)
        self.address.grid(sticky=W, padx=30)

    def buttonbox(self):
        """Redefine the buttons at the bottom of the window."""
        w = Button(self, text='Connect', width=10, command=self.ok,
                   default=ACTIVE)
        w.grid(sticky=E, padx=5, pady=5)
        self.bind('<Return>', self.ok)
        self.bind('<Escape>', self.cancel)

    def validate(self):
        """Have ConnectionStatus make a connection with the given address."""
        # noinspection PyTypeChecker
        c = ConnectionStatus(self, 'Chat Client', (self.address.get(), 8989))
        if c.connection is None:
            MessageBox(self, icon=WARNING, type=OK, title='Warning',
                       message='Could not connect to address!').show()
            return False
        self.connection = c.connection
        return True


class ConnectionStatus(Dialog):
    """ConnectionStatus(parent, title, address) -> ConnectionStatus instance"""

    def __init__(self, parent, title, address):
        """Initialize the ConnectionStatus with the server's address."""
        self.server_address = address
        self.connection = self.message = self.progress = None
        super().__init__(parent, title)

    def body(self, master):
        """Create the Dialog's widgets and start the connection process."""
        self.connection = None
        self.resizable(False, False)
        # Build Widgets
        self.message = Label(master, text='Trying to connect to address ...')
        self.progress = ProgressBar(master, orient=HORIZONTAL)
        # Place Widgets
        self.message.grid(sticky=W, padx=10, pady=2)
        self.progress.grid(sticky=EW, padx=10, pady=2)
        # Setup Widgets
        self.progress.configure(mode='indeterminate', maximum=30)
        self.progress.start()
        result = []
        start_thread(self.connect, result)
        self.after_idle(self.poll, result)

    def buttonbox(self):
        """Cancel the creation of the buttons at the bottom of this Dialog."""
        pass

    @MetaBox.thread
    def connect(self, result):
        """Try connecting to the server address that was given."""
        try:
            result.append(socket.create_connection(self.server_address, 10))
        except (socket.gaierror, socket.timeout):
            result.append(None)

    def poll(self, result):
        """Find out if the any connection information is available yet."""
        if result:
            self.connection = result[0]
            self.cancel()
        else:
            self.after(100, self.poll, result)


if __name__ == '__main__':
    log_errors(SimpleClient.main)
