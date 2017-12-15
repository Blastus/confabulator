#! /usr/bin/env python3
import select
import socket


def main():
    a = [socket.socket(socket.AF_INET, socket.SOCK_STREAM)]  # socket array
    a[0].bind(('', 8989))
    a[0].listen(5)
    while True:
        for b in select.select(a, [], [])[0]:  # ready socket
            if b is a[0]:
                a.append(b.accept()[0])
            else:
                try:
                    c = b.receive(1 << 12)  # sent message
                except socket.error:
                    b.shutdown(socket.SHUT_RDWR)
                    b.close()
                    a.remove(b)
                else:
                    for d in (d for d in a[1:] if d is not b):  # message sink
                        try:
                            d.sendall(c)
                        except ConnectionAbortedError:
                            d.shutdown(socket.SHUT_RDWR)
                            d.close()
                            a.remove(d)


if __name__ == '__main__':
    main()
