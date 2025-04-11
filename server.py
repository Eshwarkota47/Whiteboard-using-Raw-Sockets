import socket
import threading
import protocol

clients = []
session_password = "pass123"  # Change this to your desired session password

usernames = {}

def broadcast(data, source):
    for client in clients:
        if client != source:
            try:
                client.sendall(data)
            except:
                clients.remove(client)

def handle_client(client_socket):
    try:
        pw = client_socket.recv(1024).decode()
        if pw != session_password:
            client_socket.send(b"XWrong password")
            client_socket.close()
            return
        else:
            client_socket.send(b"OK")

        name = client_socket.recv(1024).decode()
        usernames[client_socket] = name
        clients.append(client_socket)

        broadcast(protocol.encode_user_list(list(usernames.values())), client_socket)

        while True:
            data = client_socket.recv(65536)
            if not data:
                break
            broadcast(data, client_socket)
    except:
        pass
    finally:
        if client_socket in clients:
            clients.remove(client_socket)
        if client_socket in usernames:
            del usernames[client_socket]
        broadcast(protocol.encode_user_list(list(usernames.values())), client_socket)
        client_socket.close()

def start_server(host='127.0.0.1', port=9999):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(10)
    print(f"[+] Server listening on {host}:{port}")
    while True:
        client_socket, addr = server.accept()
        print(f"[+] Connection from {addr}")
        threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

if __name__ == "__main__":
    start_server()
