Real-Time Whiteboard Collaboration using Raw Sockets

A lightweight, real-time collaborative whiteboard built using Python, Tkinter, and raw socket programming. This tool allows multiple users to draw, chat, and share files live in a shared canvas.

First run the server code " Python server.py "
Next open multiple teminals and run the client code on each of tem " Python client.py"
An GUI will open and asks the username , Enter the username
Next it asks for session password .By default the password is "pass123"
You can change the session password in server code
After that an whiteboard opens where you can communicate with eachother

NOTE: This uses raw sockets, so all devices (clients and server) must be on the same LAN (Local Area Network).
🚀 Features

- ✏️ Freehand Drawing and Shapes
- 💬 Real-Time Chat
- 📁 File Sharing (with size/type info + inline previews for images)
- 🔁 Undo/Redo Functionality
- 🌙 Dark Mode Toggle
- 🔐 Session-based User Authentication
- 🔄 Drag-and-Drop File Support
- 📂 Open Files Without Save Dialog

---

## 🛠️ Tech Stack

- Python (Core Logic)
- Tkinter (UI)
- Raw Sockets (Networking)
