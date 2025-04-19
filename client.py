import socket
import threading
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox, colorchooser
from tkinter.scrolledtext import ScrolledText
import os
import protocol

HOST = '127.0.0.1'
PORT = 9999

class WhiteboardClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Collaborative Whiteboard")

        self.username = simpledialog.askstring("Username", "Enter your name:", parent=self.root)
        self.password = simpledialog.askstring("Password", "Enter session password:", show='*', parent=self.root)
        self.color = "black"
        self.drawing = False
        self.last_x = self.last_y = 0
        self.tool = "draw"

        self.setup_ui()
        self.connect_to_server()

    def setup_ui(self):
        self.canvas = tk.Canvas(self.root, bg="white", width=600, height=400)
        self.canvas.grid(row=0, column=0, rowspan=20, columnspan=10, padx=5, pady=5)
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        self.chat_box = ScrolledText(self.root, width=40, height=10, state='disabled')
        self.chat_box.grid(row=21, column=0, columnspan=9, padx=5, pady=5, sticky="we")

        self.chat_entry = tk.Entry(self.root, width=30)
        self.chat_entry.grid(row=22, column=0, columnspan=7, padx=5, pady=5, sticky="we")
        self.chat_entry.bind("<Return>", lambda event: self.send_chat())

        self.send_button = tk.Button(self.root, text="Send", command=self.send_chat)
        self.send_button.grid(row=22, column=7, padx=5, pady=5, sticky="we")

        self.upload_button = tk.Button(self.root, text="Upload File", command=self.upload_file)
        self.upload_button.grid(row=22, column=8, padx=5, pady=5, sticky="we")

        self.user_list = tk.Listbox(self.root, height=20, width=20)
        self.user_list.grid(row=0, column=10, rowspan=20, padx=5, pady=5, sticky="ns")
        tk.Label(self.root, text="Online Users").grid(row=20, column=10)

        # Tools
        tk.Button(self.root, text="Draw", command=lambda: self.set_tool("draw")).grid(row=0, column=11)
        tk.Button(self.root, text="Rect", command=lambda: self.set_tool("rect")).grid(row=1, column=11)
        tk.Button(self.root, text="Circle", command=lambda: self.set_tool("circle")).grid(row=2, column=11)
        tk.Button(self.root, text="Text", command=lambda: self.set_tool("text")).grid(row=3, column=11)
        tk.Button(self.root, text="Color", command=self.choose_color).grid(row=4, column=11)
        tk.Button(self.root, text="Undo", command=self.undo).grid(row=5, column=11)
        tk.Button(self.root, text="Redo", command=self.redo).grid(row=6, column=11)
        tk.Button(self.root, text="Clear", command=self.clear_canvas).grid(row=7, column=11)

        self.history = []
        self.future = []

    def connect_to_server(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((HOST, PORT))
            self.sock.send(self.password.encode())
            response = self.sock.recv(1024).decode()
            if response.startswith("X"):
                messagebox.showerror("Error", "Wrong password!")
                self.root.destroy()
                return
            self.sock.send(self.username.encode())
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
            self.root.destroy()
            return

        threading.Thread(target=self.receive_data, daemon=True).start()

    def send_chat(self):
        msg = self.chat_entry.get().strip()
        if msg:
            full_msg = f"{self.username}: {msg}"
            self.sock.send(protocol.encode_chat(full_msg))
            self.chat_entry.delete(0, "end")

    def upload_file(self):
        path = filedialog.askopenfilename()
        if path:
            try:
                with open(path, "rb") as f:
                    data = f.read()
                self.sock.send(protocol.encode_file(path, data, self.username))
            except Exception as e:
                messagebox.showerror("File Error", str(e))

    def on_click(self, event):
        self.last_x, self.last_y = event.x, event.y
        if self.tool == "text":
            text = simpledialog.askstring("Text", "Enter text:")
            if text:
                self.canvas.create_text(event.x, event.y, text=f"{self.username}: {text}", anchor="nw", font=("Arial", 12), fill=self.color)
                self.sock.send(protocol.encode_text(event.x, event.y, text, self.username))
                self.history.append(("text", event.x, event.y, text))
        else:
            self.drawing = True

    def on_drag(self, event):
        if self.tool == "draw" and self.drawing:
            self.canvas.create_line(self.last_x, self.last_y, event.x, event.y, fill=self.color, width=2)
            self.sock.send(protocol.encode_draw(self.last_x, self.last_y, event.x, event.y))
            self.history.append(("draw", self.last_x, self.last_y, event.x, event.y))
            self.last_x, self.last_y = event.x, event.y

    def on_release(self, event):
        if self.tool in ["rect", "circle"]:
            shape_type = 'R' if self.tool == "rect" else 'C'
            if self.tool == "rect":
                self.canvas.create_rectangle(self.last_x, self.last_y, event.x, event.y, outline="blue")
            else:
                self.canvas.create_oval(self.last_x, self.last_y, event.x, event.y, outline="red")
            self.sock.send(protocol.encode_shape(shape_type, self.last_x, self.last_y, event.x, event.y))
            self.history.append((self.tool, self.last_x, self.last_y, event.x, event.y))
        self.drawing = False

    def receive_data(self):
        while True:
            try:
                data = self.sock.recv(65536)
                if not data:
                    break
                protocol.handle_incoming_data(
                    data, self.canvas, self.append_chat, self.user_list, self.handle_file)
            except Exception as e:
                print("Receive error:", e)
                break

    def append_chat(self, message):
        self.chat_box.configure(state='normal')
        self.chat_box.insert("end", message + "\n")
        self.chat_box.configure(state='disabled')
        self.chat_box.see("end")

    def handle_file(self, file_info):
        def download():
            save_path = filedialog.asksaveasfilename(initialfile=file_info["filename"])
            if save_path:
                with open(save_path, "wb") as f:
                    f.write(file_info["data"])
                messagebox.showinfo("Download", f"File saved to {save_path}")

        self.chat_box.configure(state='normal')
        self.chat_box.insert("end", f"{file_info['username']} uploaded: {file_info['filename']}  ")
        btn = tk.Button(self.chat_box, text="Download", command=download, padx=5, pady=1)
        self.chat_box.window_create("end", window=btn)
        self.chat_box.insert("end", "\n")
        self.chat_box.configure(state='disabled')
        self.chat_box.see("end")

    def set_tool(self, tool_name):
        self.tool = tool_name

    def choose_color(self):
        _, hex_color = colorchooser.askcolor(title="Choose color")
        if hex_color:
            self.color = hex_color

    def undo(self):
        if self.history:
            self.future.append(self.history.pop())
            self.redraw_canvas()

    def redo(self):
        if self.future:
            self.history.append(self.future.pop())
            self.redraw_canvas()

    def clear_canvas(self):
        self.canvas.delete("all")
        self.history.clear()
        self.future.clear()

    def redraw_canvas(self):
        self.canvas.delete("all")
        for action in self.history:
            if action[0] == "draw":
                _, x1, y1, x2, y2 = action
                self.canvas.create_line(x1, y1, x2, y2, fill="black", width=2)
            elif action[0] == "rect":
                _, x1, y1, x2, y2 = action
                self.canvas.create_rectangle(x1, y1, x2, y2, outline="blue")
            elif action[0] == "circle":
                _, x1, y1, x2, y2 = action
                self.canvas.create_oval(x1, y1, x2, y2, outline="red")
            elif action[0] == "text":
                _, x, y, text = action
                self.canvas.create_text(x, y, text=f"{self.username}: {text}", anchor="nw", font=("Arial", 12), fill="black")

if __name__ == "__main__":
    root = tk.Tk()
    app = WhiteboardClient(root)
    root.mainloop()
