import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, filedialog, colorchooser, simpledialog
import os
import time
import struct
import base64
import secrets
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# ===== Protocol Methods ===== #
class protocol:
    @staticmethod
    def encode_public_key(username, pem):
        return f"PUBLIC_KEY|{username}|".encode() + base64.b64encode(pem)

    @staticmethod
    def encode_session_key(username, encrypted_key):
        return f"SESSION_KEY|{username}|".encode() + base64.b64encode(encrypted_key)

    @staticmethod
    def encode_encrypted_chat(target, encrypted_msg):
        return f"ENCRYPTED_CHAT|{target}|".encode() + encrypted_msg

    @staticmethod
    def decode_message(data):
        parts = data.split(b"|", 2)
        if parts[0] == b"PUBLIC_KEY":
            username, rest = parts[1].decode(), base64.b64decode(parts[2])
            return ("public_key", username, rest)
        elif parts[0] == b"SESSION_KEY":
            username, rest = parts[1].decode(), base64.b64decode(parts[2])
            return ("session_key", username, rest)
        elif parts[0] == b"ENCRYPTED_CHAT":
            username, rest = parts[1].decode(), parts[2]
            return ("encrypted_chat", username, rest)
        return None

# ===== Main Client Class ===== #
class WhiteboardClient:
    def __init__(self, master):
        self.master = master
        self.master.title("Encrypted Collaborative Whiteboard")

        # Networking setup
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.username = simpledialog.askstring("Username", "Enter your username:")
        self.session_keys = {}

        # RSA Key Pair
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_key = self.private_key.public_key()

        self.setup_gui()
        self.connect_to_server()

    def setup_gui(self):
        self.canvas = tk.Canvas(self.master, bg="white", width=600, height=400)
        self.canvas.pack(padx=10, pady=10)
        self.canvas.bind("<B1-Motion>", self.paint)

        self.chat_display = scrolledtext.ScrolledText(self.master)
        self.chat_display.pack(padx=10, pady=5)
        self.chat_entry = tk.Entry(self.master)
        self.chat_entry.pack(fill=tk.X, padx=10, pady=5)
        self.chat_entry.bind("<Return>", self.send_chat)

    def paint(self, event):
        x, y = event.x, event.y
        self.canvas.create_oval(x-2, y-2, x+2, y+2, fill="black")

    def append_chat(self, message):
        self.chat_display.insert(tk.END, message + "\n")
        self.chat_display.yview(tk.END)

    def connect_to_server(self):
        self.sock.connect(("localhost", 12345))
        pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        self.sock.sendall(protocol.encode_public_key(self.username, pem))
        threading.Thread(target=self.receive_data, daemon=True).start()

    def send_chat(self, event=None):
        msg = self.chat_entry.get()
        self.chat_entry.delete(0, tk.END)
        for peer, aes_key in self.session_keys.items():
            iv = secrets.token_bytes(16)
            cipher = Cipher(algorithms.AES(aes_key), modes.CFB(iv))
            encryptor = cipher.encryptor()
            ciphertext = encryptor.update(msg.encode()) + encryptor.finalize()
            payload = base64.b64encode(iv + ciphertext)
            self.sock.sendall(protocol.encode_encrypted_chat(peer, payload))

    def receive_data(self):
        while True:
            try:
                data = self.sock.recv(4096)
                if not data:
                    break
                result = protocol.decode_message(data)
                if not result:
                    continue
                if result[0] == "public_key":
                    sender, public_pem = result[1], result[2]
                    peer_public_key = serialization.load_pem_public_key(public_pem)
                    aes_key = secrets.token_bytes(32)
                    encrypted_key = peer_public_key.encrypt(
                        aes_key,
                        padding.OAEP(
                            mgf=padding.MGF1(algorithm=hashes.SHA256()),
                            algorithm=hashes.SHA256(),
                            label=None
                        )
                    )
                    self.session_keys[sender] = aes_key
                    self.sock.sendall(protocol.encode_session_key(sender, encrypted_key))

                elif result[0] == "session_key":
                    sender, encrypted_key = result[1], result[2]
                    aes_key = self.private_key.decrypt(
                        encrypted_key,
                        padding.OAEP(
                            mgf=padding.MGF1(algorithm=hashes.SHA256()),
                            algorithm=hashes.SHA256(),
                            label=None
                        )
                    )
                    self.session_keys[sender] = aes_key

                elif result[0] == "encrypted_chat":
                    sender, payload = result[1], base64.b64decode(result[2])
                    aes_key = self.session_keys.get(sender)
                    if aes_key:
                        iv, ciphertext = payload[:16], payload[16:]
                        cipher = Cipher(algorithms.AES(aes_key), modes.CFB(iv))
                        decryptor = cipher.decryptor()
                        plain_text = decryptor.update(ciphertext) + decryptor.finalize()
                        self.append_chat(f"{sender}: {plain_text.decode()}")

            except Exception as e:
                print("Error receiving data:", e)
                break

if __name__ == '__main__':
    root = tk.Tk()
    client = WhiteboardClient(root)
    root.mainloop()