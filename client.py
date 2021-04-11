from socket import *
import threading
import sys
import os

server_name = sys.argv[1]
server_port = int(sys.argv[2])

sock = socket(AF_INET, SOCK_STREAM)
sock.connect((server_name, server_port))

sht_sock = socket(AF_INET, SOCK_STREAM)
sht_sock.connect((server_name, server_port))

while True:
    username = input('Enter username: ')

    sock.send(f"LGN {username}".encode())

    res = sock.recv(1024).decode()

    if res == "USRIN":
        print(f"{username} already logged in")
    else:
        password = input('Enter password: ')

        if res == "USRFND":
            sock.send(f"PASS {password}".encode())

            res = sock.recv(1024).decode()

            if res == "CORRPASS":
                break
            elif res == "INCORPASS":
                print("Invalid password")
        elif res == "NOUSR":
            sock.send(f"PASS {password}".encode())

            res = sock.recv(1024).decode()

            if res == "NEWUSR":
                break

def handle_shutdown(conn, main):
    alive = True

    while alive:
        res = conn.recv(1024).decode()

        if res == "SHT":
            print("\n\nServer is shutting down")
            break
    main.close()
    conn.close()
    os._exit(0)
    

t = threading.Thread(name="shtHandler", target=handle_shutdown, args=(sht_sock,sock))
t.daemon = True
t.start()

print("Welcome to the server")

while True:
    
    command = input("Enter one of the following commands: CRT, MSG, DLT, EDT, LST, RDT, UPD, DWN, RMV, XIT, SHT: ").split()

    if len(command) == 0:
        continue
    elif command[0] == "CRT":
        if len(command) != 2:
            print("Usage: CRT <threadtitle>")
        else:
            sock.send(f"CRT {command[1]} {username}".encode())

            res = sock.recv(1024).decode()

            if res == "THDEXST":
                print(f"Thread {command[1]} already exists")
            elif res == "THRDCRT":
                print(f"Thread {command[1]} created")
    elif command[0] == "MSG":
        if len(command) < 3:
            print("Usage: MSG <threadtitle> <message>")
        else:
            sock.send(f"MSG {command[1]} {username} {' '.join(command[2:])}".encode())

            res = sock.recv(1024).decode()

            if res == "NOTHRD":
                print(f"Thread {command[1]} does not exist")
            elif res == "MSGCRT":
                print(f"Message posted to {command[1]} thread")
    elif command[0] == "DLT":
        try:
            int(command[2])
        except:
            print("Usage: DLT <threadtitle> <messagenumber>")
            continue

        if len(command) != 3:
            print("Usage: DLT <threadtitle> <messagenumber>")
        else:
            sock.send(f"DLT {command[1]} {command[2]} {username}".encode())

            res = sock.recv(1024).decode()

            if res == "INVMSGN":
                print(f"Message number {command[2]} invalid")
            elif res == "INVUSR":
                print("User did not send message")
            elif res == "MSGDLT":
                print(f"Message {command[2]} deleted")
    elif command[0] == "EDT":
        try:
            int(command[2])
        except:
            print("Usage: EDT <threadtitle> <messagenumber> <message>")
            continue

        if len(command) < 4:
            print("Usage: EDT <threadtitle> <messagenumber> <message>")
        else:
            sock.send(f"EDT {command[1]} {command[2]} {username} {' '.join(command[3:])}".encode())

            res = sock.recv(1024).decode()

            if res == "INVMSGN":
                print(f"Message number {command[2]} invalid")
            elif res == "INVUSR":
                print("User did not send message")
            elif res == "MSGEDT":
                print(f"Message {command[2]} edited")
    elif command[0] == "LST":
        if len(command) > 1:
            print("Usage: LST")
            continue
        
        sock.send("LST".encode())

        res = sock.recv(1024).decode()

        threads = res.split()

        if res == "NOTHRD":
            print("No threads to list")
        else:
            print("Active threads:")
            for t in threads:
                print(f"    {t}")
    elif command[0] == "RDT":
        if len(command) != 2:
            print("Usage: RDT <threadtitle>")
            continue

        sock.send(' '.join(command).encode())

        res = sock.recv(1024).decode()

        if res == "NOTHRD":
            print("Invalid thread name")
        elif res == "EMPTY":
            print(f"Thread {command[1]} is empty")
        else:
            print(f"Messages in thread {command[1]}")
            for msg in res.rstrip().split('\n'):
                print(f"    {msg}")
    elif command[0] == "UPD":
        if len(command) != 3:
            print("Usage: UPD <threadtitle> <filename>")
            continue
        
        if not os.path.isfile(command[2]):
            print("File does not exist")
            continue

        sock.send(f"{' '.join(command)} {username}".encode())

        res = sock.recv(1024).decode()

        if res == "NOTHRD":
            print("Invalid thread title")
        elif res == "INVLDFILE":
            print("File with that name already exists")
        elif res == "VLDFILE":
            print("Uploading file...")
            
            with open(command[2], 'rb') as f:
                sock.send(f"{os.path.getsize(command[2])}".encode())
                b = f.read(1024)
                while b:
                    sock.send(b)
                    b = f.read(1024)
            
            if sock.recv(1024).decode() == "FILEUPLD":
                print(f"File uploaded to thread {command[1]}")
    elif command[0] == "DWN":
        if len(command) != 3:
            print("Usage: DWN <threadtitle> <filename>")
            continue
        
        if os.path.isfile(command[2]):
            print("File already exists")
            continue

        sock.send(f"{' '.join(command)} {username}".encode())

        res = sock.recv(1024).decode()

        if res == "NOTHRD":
            print("Invalid thread title")
        elif res == "INVLDFILE":
            print("File with that name already exists")
        else:
            print("Downloading...")
            transferred = 0
            length = int(res)

            with open(command[2], 'wb') as f:
                data = sock.recv(1024)
                transferred += len(data)

                if transferred >= length:
                    f.write(data)

                while transferred < length and data != b'':
                    f.write(data)
                    data = sock.recv(1024)
                    transferred += len(data)

            sock.send(b"FILERECV")
            print("File downloaded")
    elif command[0] == "RMV":
        if len(command) != 2:
            print("Usage: RMV <threadtitle>")
            continue

        sock.send(f"{' '.join(command)} {username}".encode())

        sock.recv(1024).decode()

        if res == "NOTHRD":
            print("Invalid thread name")
        elif res == "INVUSR":
            print("User is not creator of thread")
        elif res == "THDRMV":
            print(f"Thread {command[1]} deleted")
    elif command[0] == "XIT":
        if len(command) != 1:
            print("Usage: XIT")
            continue
        
        sock.send("XIT".encode())

        print("Shutting down")
        break
    elif command[0] == "SHT":
        if len(command) != 2:
            print("Usage: SHT <admin_password>")
            continue

        sock.send(' '.join(command).encode())
    else:
        print("Invalid command")