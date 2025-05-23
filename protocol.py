import struct
import os

# -- Message Encoding Functions --

def encode_draw(x1, y1, x2, y2):
    return b'D' + struct.pack('!4H', x1, y1, x2, y2)

def encode_shape(shape_type, x1, y1, x2, y2):
    return shape_type.encode() + struct.pack('!4H', x1, y1, x2, y2)

def encode_text(x, y, text, username=""):
    payload = f"{username}: {text}" if username else text
    return b'T' + struct.pack('!2H', x, y) + payload.encode()

def encode_chat(message):
    return b'M' + message.encode()

def encode_file(filename, data, username=""):
    basename = os.path.basename(filename)
    header = f"F{username}|{basename}|".encode()
    return header + data

def encode_user_list(usernames):
    return b'U' + '|'.join(usernames).encode()

# -- Incoming Message Handler --

def handle_incoming_data(data, canvas, append_chat, user_list, handle_file_callback=None):
    cmd = data[0:1]

    if cmd == b'D':
        x1, y1, x2, y2 = struct.unpack('!4H', data[1:9])
        canvas.create_line(x1, y1, x2, y2, fill="black", width=2)
        return ("draw", x1, y1, x2, y2)

    elif cmd in [b'R', b'C']:
        x1, y1, x2, y2 = struct.unpack('!4H', data[1:9])
        if cmd == b'R':
            canvas.create_rectangle(x1, y1, x2, y2, outline="blue")
            return ("rect", x1, y1, x2, y2)
        else:
            canvas.create_oval(x1, y1, x2, y2, outline="red")
            return ("circle", x1, y1, x2, y2)

    elif cmd == b'T':
        x, y = struct.unpack('!2H', data[1:5])
        text = data[5:].decode()
        canvas.create_text(x, y, text=text, anchor="nw", font=("Arial", 12), fill="black")
        return ("text", x, y, text)

    elif cmd == b'M':
        msg = data[1:].decode()
        append_chat(msg)

    elif cmd == b'F':
        try:
            rest = data[1:]
            parts = rest.split(b'|', 2)
            if len(parts) != 3:
                print("[!] Invalid file message format")
                return
            username = parts[0].decode()
            filename = parts[1].decode()
            content = parts[2]

            ext = os.path.splitext(filename)[1].lower()
            if ext not in [".txt", ".png", ".jpg", ".jpeg", ".pdf"]:
                print("[!] Unsupported file type:", filename)
                return

            os.makedirs("uploads", exist_ok=True)
            filepath = os.path.join("uploads", filename)
            with open(filepath, "wb") as f:
                f.write(content)

            if handle_file_callback:
                handle_file_callback({
                    "username": username,
                    "filename": filename,
                    "data": content,
                    "size": len(content),
                    "type": ext,
                    "filepath": filepath
                })

            # ❌ REMOVED this line to avoid duplicate:
            # append_chat(f"{username} uploaded: {filename}")

        except Exception as e:
            print("[!] Error handling file:", e)

    elif cmd == b'U':
        users = data[1:].decode().split('|')
        user_list.delete(0, "end")
        for user in users:
            user_list.insert("end", user)

    return None
