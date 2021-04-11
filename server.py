from os import name
from os.path import isfile
from socket import *

import queue
from sys import path
import threading
import os
import re
import sys

server_port = int(sys.argv[1])
admin_passwd = sys.argv[2]

stop = False

lock = threading.Condition()

users = []
clients = []

def get_line_num(str):
    i = re.search('^([0-9])', str)
    return int(i.group(1)) if i is not None else -1

def write_to_cred(line):
    with open('credentials.txt', 'a') as f:
        f.write(f"\n{line}")

def create_thread(name, user):
    if not os.path.isfile(name):
        with open(name, 'w') as f:
            f.write(f"{user}\n")

def write_to_thread(thread, name, n, message):
    with open(thread, 'a') as f:
        f.write(f"{n} {name}: {message}\n")

def delete_message(thread, n):
    with open(thread, 'r') as f:
        with open(f".{thread}", 'w') as tmp:
            for line in f:
                i = get_line_num(line)

                if i < n:
                    tmp.write(f"{line.rstrip()}\n")
                elif i > n:
                    msg = re.search('^[0-9](.*)$', line)
                    if msg is not None:
                        tmp.write(f"{i - 1}{msg.group(1).rstrip()}\n")
    os.remove(thread)
    os.rename(f".{thread}", thread)

def edit_message(thread, n, name, message):
    with open(thread, 'r') as f:
        with open(f".{thread}", 'w') as tmp:
            for line in f:
                if get_line_num(line) != n:
                    tmp.write(f"{line.rstrip()}\n")
                else:
                    tmp.write(f"{n} {name}: {message}\n")
    
    os.remove(thread)
    os.rename(f".{thread}", thread)

def write_file_to_thread(thread, name, filename):
    with open(thread, 'a') as f:
        f.write(f"{name} uploaded {filename}\n")

def remove_thread(thread, files):
    os.remove(thread)
    for f in files:
        os.remove(f)

def usr_handler(conn, q, sht):
    global stop, users
    logged_in, u_name, pswrd = False, None, None
    
    print("Client connected")

    while not stop:
        cmd = conn.recv(1024).decode().split()

        if not cmd:
            break

        if len(cmd) < 1:
            continue
        
        if not logged_in:
            if cmd[0] == 'LGN':
                f = open('credentials.txt', 'r')

                u_name = cmd[1]

                for line in f:
                    if line.split()[0] == u_name:
                        pswrd = line.split()[1]
                        break
                
                if pswrd is None:
                    conn.send(b'NOUSR')
                elif u_name in users:
                    print(f"{u_name} already logged in")
                    u_name = ''
                    conn.send(b'USRIN')
                else:
                    conn.send(b'USRFND')

                f.close()
            elif cmd[0] == 'PASS':
                if pswrd is None:
                    q.put(lambda: write_to_cred(f"{u_name} {cmd[1]}"))
                    conn.send(b"NEWUSR")
                    logged_in = True
                else:
                    if cmd[1] == pswrd:
                        conn.send(b'CORRPASS')
                        logged_in = True
                    else:
                        conn.send(b'INCORPASS')
                
                if logged_in:
                    print(f"{u_name} successfully logged in")
                    users.pop()
                    users.append(u_name)
        else:
            print(f"{u_name} issued {cmd[0]} command")

            if cmd[0] == 'CRT':
                if os.path.isfile(cmd[1]):
                    print(f"Thread {cmd[1]} already exists")
                    conn.send(b'THDEXST')
                else:
                    print(f"Thread {cmd[1]} created")
                    q.put(lambda: create_thread(cmd[1], cmd[2]))
                    conn.send(b'THRDCRT')
            elif cmd[0] == 'MSG':
                if not os.path.isfile(cmd[1]):
                    print(f"No thread {cmd[1]}")
                    conn.send(b"NOTHRD")
                else:
                    num = 1

                    with open(cmd[1], 'rb') as f:
                        start = f.readline().decode()
                        
                        f.seek(0, os.SEEK_END)
                        f.seek(-2, 2)

                        while f.tell() >= 1 and f.read(1) != b'\n':
                            if (f.tell() != 1):
                                f.seek(-2, 1)
                            else:
                                f.seek(-1, 1)
                                break

                        line = f.read().decode()
                        
                        if line != start:
                            num = int(re.search('^([0-9])', line).group(1)) + 1
                    
                    print(f"{cmd[2]} posted message in {cmd[1]}")
                    conn.send(b"MSGCRT")

                    q.put(lambda: write_to_thread(cmd[1], cmd[2], num, ' '.join(cmd[3:])))
            elif cmd[0] == 'DLT':
                if not os.path.isfile(cmd[1]):
                    print(f"No thread {cmd[1]}")
                    conn.send(b"NOTHRD")
                else:
                    n, usr = -1, None

                    with open(cmd[1], 'r') as f:
                        next(f)

                        for line in f:
                            n = get_line_num(line)

                            if n == int(cmd[2]):
                                usr = line.split()[1][:-1]
                                break

                    if n != int(cmd[2]):
                        print(f"Invalid message number {cmd[2]}")
                        conn.send(b"INVMSGN")
                    elif usr != cmd[3]:
                        print(f"{cmd[3]} not sender of message")
                        conn.send(b"INVUSR")
                    else:
                        print(f"Deleted message {cmd[2]}")
                        q.put(lambda: delete_message(cmd[1], int(cmd[2])))
                        conn.send(b"MSGDLT")
            elif cmd[0] == "EDT":
                if not os.path.isfile(cmd[1]):
                    print(f"No thread {cmd[1]}")
                    conn.send(b"NOTHRD")
                else:
                    n, usr = -1, None

                    with open(cmd[1], 'r') as f:
                        next(f)

                        for line in f:
                            n = get_line_num(line)

                            if n == int(cmd[2]):
                                usr = line.split()[1][:-1]
                                break

                    if n != int(cmd[2]):
                        print(f"Invalid message number {cmd[2]}")
                        conn.send(b"INVMSGN")
                    elif usr != cmd[3]:
                        print(f"{cmd[3]} not sender of message")
                        conn.send(b"INVUSR")
                    else:
                        print(f"Edited message {cmd[2]}")
                        q.put(lambda: edit_message(cmd[1], int(cmd[2]), cmd[3], ' '.join(cmd[4:])))
                        conn.send(b"MSGEDT")
            elif cmd[0] == 'LST':
                files = ' '.join([f for f in os.listdir('.') if os.path.isfile(f)
                    and f not in ['client.py', 'server.py', 'credentials.txt']])

                if files is '':
                    conn.send(b'NOTHRD')

                conn.send(files.encode())
            elif cmd[0] == 'RDT':
                try:
                    with open(cmd[1]) as f:
                            next(f)
                            msgs = f.read()
                    if msgs is not '':
                        conn.send(msgs.encode())
                    else:
                        conn.send(b"EMPTY")
                    print(f"Thread {cmd[1]} read")
                except:
                    print(f"No thread {cmd[1]}")
                    conn.send(b"NOTHRD")
            elif cmd[0] == "UPD":
                if not os.path.isfile(cmd[1]):
                    print(f"No thread {cmd[1]}")
                    conn.send(b"NOTHRD")
                elif os.path.isfile(f"{cmd[1]}-{cmd[2]}"):
                    print(f"{cmd[2]} already exists")
                    conn.send(b'INVLDFILE')
                else:
                    print(f"{cmd[2]} uploading...")
                    conn.send(b'VLDFILE')

                    transferred = 0
                    length = int(conn.recv(1024).decode())

                    with open(f"{cmd[1]}-{cmd[2]}", 'wb') as f:
                        data = conn.recv(1024)
                        transferred += len(data)

                        if transferred >= length:
                            f.write(data)

                        while transferred < length and data != b'':
                            f.write(data)
                            data = conn.recv(1024)
                            transferred += len(data)
                    conn.send(b"FILEUPLD")
                    print(f"{cmd[2]} uploaded")
                    q.put(lambda: write_file_to_thread(cmd[1], cmd[3], cmd[2]))
            elif cmd[0] == "DWN":
                if not os.path.isfile(cmd[1]):
                    print(f"No thread {cmd[1]}")
                    conn.send(b"NOTHRD")
                elif not os.path.isfile(f"{cmd[1]}-{cmd[2]}"):
                    print(f"{cmd[2]} doesn't exist")
                    conn.send(b'INVLDFILE')
                else:
                    print("Sending file")
                    filename = f"{cmd[1]}-{cmd[2]}"
                    with open(filename, 'rb') as f:
                        conn.send(f"{os.path.getsize(filename)}".encode())
                        b = f.read(1024)
                        while b:
                            conn.send(b)
                            b = f.read(1024)
                    if conn.recv(1024).decode() == "FILERECV":
                        print("File transferred")
            elif cmd[0] == "RMV":
                if not os.path.isfile(cmd[1]):
                    print(f"No thread {cmd[1]}")
                    conn.send(b"NOTHRD")
                else:
                    files = []

                    with open(cmd[1]) as f:
                        creator = f.readline().rstrip()

                        if creator != cmd[2]:
                            print(f"{cmd[2]} is not creator of thread")
                            conn.send(b'INVUSR')
                            continue 
                        else:
                            for line in f:
                                if get_line_num(line) == -1:
                                    files.append(f"{cmd[1]}-{line.split()[2]}")
                    print(f"{cmd[1]} deleted")
                    q.put(lambda: remove_thread(cmd[1], files))
                    conn.send(b"THDRMV")
            elif cmd[0] == "XIT":
                break
            elif cmd[0] == "SHT":
                if cmd[1] != admin_passwd:
                    conn.send(b"INPASS")
                else:
                    shutdown()
            else:
                print(f"Invalid command")
    if logged_in:
        print(f"{u_name} disconnected")
        users.remove(u_name)
    else:
        print("Client disconnected")
    conn.close()

def file_handler(q):
    global stop

    while not stop:
        if not q.empty():
            act = q.get()
            act()

sock = socket(AF_INET, SOCK_STREAM)
sock.bind(('127.0.0.1', server_port))
sock.listen(1)

file_queue = queue.Queue()

file_thread = threading.Thread(name="fileHandler", target=file_handler, args=(file_queue,))
file_thread.start()

def shutdown():
    global stop, sock
    if not stop:
        for c in clients:
            c.send(b"SHT")
            clients.remove(c)
        stop = True

        for f in [f for f in os.listdir('.') if os.path.isfile(f)
                    and f not in ['client.py', 'server.py']]:
            os.remove(f)
        
        sock.shutdown(SHUT_RD)
        sock.close()
        print("Shutting down")
        os._exit(0)

while not stop:
    if len(users) == 0:
        print("Waiting for clients")

    try:
        conn, _ = sock.accept()
        sht, _ = sock.accept()
        clients.append(sht)
        users.append('')
        usr_thread = threading.Thread(name="userHandler", target=usr_handler, args=(conn, file_queue, sht))
        usr_thread.daemon=True
        usr_thread.start()
    except KeyboardInterrupt:
        stop = True
        for c in clients:
            c.send(b"SHT")
            clients.remove(c)
        sock.shutdown(SHUT_RD)
        sock.close()
        sys.exit()
