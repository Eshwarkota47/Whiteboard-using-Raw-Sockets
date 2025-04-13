import socket
import threading
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox, scrolledtext, colorchooser
from tkinterdnd2 import DND_FILES, TkinterDnD
import protocol
import os
import html
from tkinter import ttk
import io
import fitz  # PyMuPDF
import webbrowser

class WhiteboardClient:
    def __init__(self):
        self.root = TkinterDnD.Tk()
        self.root.title("🎨 Real-Time Collaborative Whiteboard")
        self.dark_mode = False

        self.mode = "draw"
        self.draw_color = "#2c3e50"
        self.start_x = self.start_y = None
        self.history = []
        self.redo_stack = []

        self.username = simpledialog.askstring("Username", "Enter your name:")

        self.canvas = tk.Canvas(self.root, bg='white', width=800, height=500, relief=tk.RIDGE, bd=5, highlightthickness=3, highlightbackground="#95a5a6")
        self.canvas.grid(row=0, column=0, columnspan=5, padx=10, pady=10)
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        self.canvas.drop_target_register(DND_FILES)
        self.canvas.dnd_bind('<<Drop>>', self.on_drop)

        self.preview_frame = tk.Frame(self.root, bg="#dfe6e9")
        self.preview_frame.grid(row=0, column=5, rowspan=5, padx=5, pady=5)

        self.preview_label = tk.Label(self.preview_frame, text="File Preview", bg="#b2bec3", width=25, height=15, relief=tk.GROOVE)
        self.preview_label.pack()

        self.button_frame = tk.Frame(self.preview_frame, bg="#dfe6e9")
        self.button_frame.pack(pady=5)
        self.prev_button = ttk.Button(self.button_frame, text="Previous", command=self.prev_page)
        self.next_button = ttk.Button(self.button_frame, text="Next", command=self.next_page)
        self.zoom_button = ttk.Button(self.button_frame, text="Zoom", command=self.toggle_zoom)
        self.download_button = ttk.Button(self.button_frame, text="Open", command=self.open_file)
        self.prev_button.grid(row=0, column=0)
        self.next_button.grid(row=0, column=1)
        self.zoom_button.grid(row=0, column=2)
        self.download_button.grid(row=0, column=3)

        self.current_pdf = None
        self.current_page = 0
        self.zoomed = False
        self.last_previewed_file = None

        self.create_toolbar()
        self.create_chat_box()
        self.create_user_list()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect_to_server()

        threading.Thread(target=self.receive_data, daemon=True).start()

    def open_file(self):
        if self.last_previewed_file:
            webbrowser.open(self.last_previewed_file)

    def connect_to_server(self):
        self.sock.connect(("127.0.0.1", 9999))
        pw = simpledialog.askstring("Session Password", "Enter session password:")
        self.sock.sendall(pw.encode())
        response = self.sock.recv(1024)
        if response.startswith(b"X"):
            messagebox.showerror("Error", "Wrong password")
            self.sock.close()
            self.root.after(100, self.root.destroy)
        else:
            self.sock.sendall(self.username.encode())
            print("[+] Connected")

    def create_toolbar(self):
        frame = tk.Frame(self.root, bg="#ecf0f1")
        frame.grid(row=1, column=0, columnspan=5, sticky="ew", padx=10, pady=5)
        for tool in ["draw", "rect", "circle", "text"]:
            ttk.Button(frame, text=tool.title(), command=lambda t=tool: self.set_mode(t)).pack(side=tk.LEFT, padx=3)
        ttk.Button(frame, text="Color", command=self.choose_color).pack(side=tk.LEFT, padx=3)
        ttk.Button(frame, text="Undo", command=self.undo).pack(side=tk.LEFT, padx=3)
        ttk.Button(frame, text="Redo", command=self.redo).pack(side=tk.LEFT, padx=3)
        ttk.Button(frame, text="Clear", command=self.clear).pack(side=tk.LEFT, padx=3)
        ttk.Button(frame, text="Upload File", command=self.send_file).pack(side=tk.LEFT, padx=3)
        ttk.Button(frame, text="Toggle Dark Mode", command=self.toggle_dark_mode).pack(side=tk.LEFT, padx=3)

    def create_chat_box(self):
        self.chat_display = scrolledtext.ScrolledText(self.root, height=10, width=80, state='disabled', bg="#fdfbfb")
        self.chat_display.grid(row=2, column=0, columnspan=4, padx=10, pady=5)
        self.chat_entry = ttk.Entry(self.root, width=50)
        self.chat_entry.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        self.chat_send = ttk.Button(self.root, text="Send", command=self.send_chat)
        self.chat_send.grid(row=3, column=1, pady=5)

    def create_user_list(self):
        self.user_list = tk.Listbox(self.root, height=10, width=25, bg="#f0f8ff", border=2)
        self.user_list.grid(row=2, column=4, rowspan=2, padx=5, pady=5)

    def choose_color(self):
        color = colorchooser.askcolor(title="Choose drawing color")[1]
        if color:
            self.draw_color = color

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        bg = '#2d3436' if self.dark_mode else 'white'
        fg = 'white' if self.dark_mode else 'black'
        self.canvas.config(bg=bg)
        self.chat_display.config(bg=bg, fg=fg)
        self.preview_frame.config(bg='#2d3436' if self.dark_mode else '#dfe6e9')
        self.preview_label.config(bg='#636e72' if self.dark_mode else '#b2bec3', fg=fg)
        self.button_frame.config(bg='#2d3436' if self.dark_mode else '#dfe6e9')

    def set_mode(self, mode):
        self.mode = mode

    def on_click(self, event):
        self.start_x, self.start_y = event.x, event.y
        if self.mode == "text":
            text = simpledialog.askstring("Text", "Enter text:")
            if text:
                safe_text = html.escape(f"{self.username}: {text}")
                self.canvas.create_text(event.x, event.y, text=safe_text, anchor="nw", fill=self.draw_color, font=("Helvetica", 12, "bold"))
                self.sock.sendall(protocol.encode_text(event.x, event.y, safe_text))
                self.history.append(("text", event.x, event.y, safe_text))

    def on_drag(self, event):
        if self.mode == "draw":
            self.canvas.create_line(self.start_x, self.start_y, event.x, event.y, fill=self.draw_color, width=2, capstyle=tk.ROUND, smooth=True)
            self.sock.sendall(protocol.encode_draw(self.start_x, self.start_y, event.x, event.y))
            self.history.append(("draw", self.start_x, self.start_y, event.x, event.y))
            self.start_x, self.start_y = event.x, event.y

    def on_release(self, event):
        if self.mode in ["rect", "circle"]:
            if self.mode == "rect":
                self.canvas.create_rectangle(self.start_x, self.start_y, event.x, event.y, outline=self.draw_color, width=2)
                self.sock.sendall(protocol.encode_shape("R", self.start_x, self.start_y, event.x, event.y))
                self.history.append(("rect", self.start_x, self.start_y, event.x, event.y))
            elif self.mode == "circle":
                self.canvas.create_oval(self.start_x, self.start_y, event.x, event.y, outline=self.draw_color, width=2)
                self.sock.sendall(protocol.encode_shape("C", self.start_x, self.start_y, event.x, event.y))
                self.history.append(("circle", self.start_x, self.start_y, event.x, event.y))

    def undo(self):
        if self.history:
            item = self.history.pop()
            self.redo_stack.append(item)
            self.canvas.delete("all")
            self.replay_history()

    def redo(self):
        if self.redo_stack:
            item = self.redo_stack.pop()
            self.history.append(item)
            self.canvas.delete("all")
            self.replay_history()

    def clear(self):
        self.canvas.delete("all")
        self.history.clear()
        self.redo_stack.clear()

    def replay_history(self):
        for item in self.history:
            if item[0] == "draw":
                _, x1, y1, x2, y2 = item
                self.canvas.create_line(x1, y1, x2, y2, fill=self.draw_color, width=2)
            elif item[0] == "rect":
                _, x1, y1, x2, y2 = item
                self.canvas.create_rectangle(x1, y1, x2, y2, outline=self.draw_color, width=2)
            elif item[0] == "circle":
                _, x1, y1, x2, y2 = item
                self.canvas.create_oval(x1, y1, x2, y2, outline=self.draw_color, width=2)
            elif item[0] == "text":
                _, x, y, text = item
                self.canvas.create_text(x, y, text=text, anchor="nw", fill=self.draw_color, font=("Helvetica", 12, "bold"))

    def send_chat(self):
        msg = self.chat_entry.get()
        self.chat_entry.delete(0, tk.END)
        if len(msg) > 500:
            messagebox.showwarning("Too long", "Message too long (max 500 characters)")
            return
        safe_msg = html.escape(msg)
        full_msg = f"{self.username}: {safe_msg}"
        self.sock.sendall(protocol.encode_chat(full_msg))
        self.append_chat(full_msg)

    def append_chat(self, msg):
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, msg + "\n")
        self.chat_display.config(state='disabled')
        self.chat_display.yview(tk.END)

    def send_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("Allowed files", "*.txt *.png *.jpg *.jpeg *.pdf")])
        if filepath and os.path.getsize(filepath) < 5 * 1024 * 1024:
            self.preview_file(filepath)
            with open(filepath, "rb") as f:
                content = f.read()
                self.sock.sendall(protocol.encode_file(os.path.basename(filepath), content))
                status_msg = f"{self.username} uploaded: {filepath}"
                self.sock.sendall(protocol.encode_chat(status_msg))
                self.append_chat(status_msg)
        else:
            messagebox.showwarning("Warning", "File too large or unsupported format")

    def on_drop(self, event):
        filepath = event.data.strip('{}')
        if os.path.isfile(filepath) and filepath.lower().endswith((".txt", ".png", ".jpg", ".jpeg", ".pdf")):
            if os.path.getsize(filepath) < 5 * 1024 * 1024:
                self.preview_file(filepath)
                with open(filepath, "rb") as f:
                    content = f.read()
                    self.sock.sendall(protocol.encode_file(os.path.basename(filepath), content))
                    status_msg = f"{self.username} dropped: {filepath}"
                    self.sock.sendall(protocol.encode_chat(status_msg))
                    self.append_chat(status_msg)

    def preview_file(self, filepath):
        self.last_previewed_file = filepath
        if filepath.lower().endswith(".pdf"):
            self.current_pdf = fitz.open(filepath)
            self.current_page = 0
            self.show_pdf_page()

    def show_pdf_page(self):
        if self.current_pdf:
            zoom = 2 if self.zoomed else 1
            page = self.current_pdf.load_page(self.current_page)
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            img_bytes = pix.tobytes("ppm")
            img_stream = io.BytesIO(img_bytes)
            self.preview_label.config(text="PDF Page Loaded (image removed)", image="")

    def prev_page(self):
        if self.current_pdf and self.current_page > 0:
            self.current_page -= 1
            self.show_pdf_page()

    def next_page(self):
        if self.current_pdf and self.current_page < len(self.current_pdf) - 1:
            self.current_page += 1
            self.show_pdf_page()

    def toggle_zoom(self):
        self.zoomed = not self.zoomed
        self.show_pdf_page()

    def receive_data(self):
        while True:
            try:
                data = self.sock.recv(65536)
                if data:
                    result = protocol.handle_incoming_data(data, self.canvas, self.append_chat, self.user_list)
                    if result and result[0] in ["draw", "rect", "circle", "text"]:
                        self.history.append(result)
            except:
                break

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    WhiteboardClient().run()
