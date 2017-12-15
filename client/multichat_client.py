#! /usr/bin/env python3
import socket
import sys
from tkinter.constants import *

from client.safetkinter import *


class ConfabulatorClient(Frame):
    after_handle = None

    def __init__(self, master, remote_host):
        super().__init__(master)
        self.message_area = ScrolledText(self, width=81, height=21,
                                         wrap=WORD, state=DISABLED)
        self.message_area.grid(sticky=NSEW, columnspan=2)
        self.send_area = Entry(self)
        self.send_area.bind('<Return>', self.key_pressed)
        self.send_area.grid(sticky=EW)
        b = Button(self, text='Send', command=self.mouse_clicked)
        b.grid(row=1, column=1)
        self.send_area.focus_set()
        try:
            self.remote = socket.create_connection((remote_host, 8989))
        except socket.gaierror:
            print(f'Could not find host {remote_host}.')
        except socket.error:
            print(f'Could not connect to host {remote_host}.')
        else:
            self.remote.setblocking(False)
            self.after_handle = self.after_idle(self.data_ready)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

    @classmethod
    def main(cls, args):
        root = Tk()
        root.title('ConfabulatorClient version 1.0')
        m = cls(root, args[0])
        m.grid(sticky=NSEW)
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)
        root.mainloop()
        return 1

    def data_ready(self):
        try:
            s = self.remote.receive(1 << 12).decode()
        except socket.error:
            pass
        else:
            self.message_area['state'] = NORMAL
            self.message_area.insert(END, s)
            self.message_area['state'] = DISABLED
            self.message_area.see(END)
        self.after_handle = self.after(100, self.data_ready)

    def destroy(self):
        if self.after_handle:
            self.after_cancel(self.after_handle)
        super().destroy()

    def mouse_clicked(self, _=None):
        self.remote.sendall(self.send_area.get().encode() + b'\r\n')
        self.send_area.delete(0, END)

    key_pressed = mouse_clicked


if __name__ == '__main__':
    sys.exit(ConfabulatorClient.main(sys.argv[1:]))
