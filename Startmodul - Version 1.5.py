import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
import logging
import os
import shutil
import keyboard
import whoosh.index as index
from whoosh.qparser import QueryParser
from whoosh.fields import Schema, TEXT, ID
import threading
import ctypes
import random

log_file = os.path.join(os.path.dirname(__file__), 'user_logbook.log')
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

users = {
    "ITC-Schüler": {"rolle": "Schüler", "passwort": "14352045a", "laufwerk": "C:\\"},
    "ITC-Chris-Wollinger": {"rolle": "Lehrer", "passwort": "werter2", "laufwerk": "C:\\"}
}

class LockScreen(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Anmeldung erforderlich")
        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.configure(background='black')

        hwnd = ctypes.windll.user32.FindWindowW(None, self.title())
        ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002)

        self.protocol("WM_DELETE_WINDOW", self.disable_event)
        self.disable_hotkeys()

        self.canvas = tk.Canvas(self, width=self.winfo_screenwidth(), height=self.winfo_screenheight(), highlightthickness=0, bg='black')
        self.canvas.pack(fill="both", expand=True)

        self.logo = tk.PhotoImage(file="logo.png")  # Ensure logo.png exists in the same directory
        self.logo_item = self.canvas.create_image(100, 100, image=self.logo, anchor=tk.NW)
        self.dx = 4
        self.dy = 3
        self.animate_logo()

        self.create_login_module()

    def disable_event(self):
        pass

    def disable_hotkeys(self):
        blocked_keys = ['alt+tab', 'alt+f4', 'win+l', 'ctrl+esc', 'esc', 'win']
        for key in blocked_keys:
            keyboard.add_hotkey(key, lambda: None)

    def animate_logo(self):
        self.canvas.move(self.logo_item, self.dx, self.dy)
        coords = self.canvas.coords(self.logo_item)
        if coords[0] <= 0 or coords[0] + self.logo.width() >= self.winfo_screenwidth():
            self.dx = -self.dx
        if coords[1] <= 0 or coords[1] + self.logo.height() >= self.winfo_screenheight():
            self.dy = -self.dy
        self.after(20, self.animate_logo)

    def create_login_module(self):
        login_frame = tk.Frame(self.canvas, bg='#2b2b2b', padx=40, pady=40, bd=2, relief=tk.RIDGE)
        login_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        tk.Label(login_frame, text="Anmeldung erforderlich", font=('Segoe UI', 20, 'bold'), bg='#2b2b2b', fg='white').pack(pady=(0, 20))
        tk.Label(login_frame, text="Benutzername", font=('Segoe UI', 12), bg='#2b2b2b', fg='white').pack(anchor='w')
        self.username_entry = tk.Entry(login_frame, font=('Segoe UI', 12), width=30)
        self.username_entry.pack(pady=(0, 10))

        tk.Label(login_frame, text="Passwort", font=('Segoe UI', 12), bg='#2b2b2b', fg='white').pack(anchor='w')
        self.password_entry = tk.Entry(login_frame, show="*", font=('Segoe UI', 12), width=30)
        self.password_entry.pack(pady=(0, 20))

        tk.Button(login_frame, text="Anmelden", command=self.check_login, font=('Segoe UI', 12), bg='#0078D7', fg='white', activebackground='#005a9e', relief=tk.FLAT).pack(ipadx=10, ipady=2)

    def check_login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        if username in users and users[username]["passwort"] == password:
            messagebox.showinfo("Anmeldung erfolgreich", f"Willkommen, {username}!")
            self.destroy()
            self.start_file_explorer(username)
        else:
            messagebox.showerror("Fehler", "Ungültiger Benutzername oder Passwort.")

    def start_file_explorer(self, username):
        root = tk.Toplevel(self)
        FileExplorer(root, username)

class FileExplorer:
    def __init__(self, root, username):
        self.root = root
        self.username = username
        self.root.title("Datei Explorer")
        self.root.geometry("800x600")
        self.tree = ttk.Treeview(self.root)
        self.tree.pack(expand=True, fill=tk.BOTH)
        self.base_path = users[self.username]["laufwerk"]
        self.populate_tree(self.base_path)

        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Suchen", command=self.search_files)
        self.tree.bind("<Button-3>", self.popup_menu)

    def populate_tree(self, path):
        self.tree.delete(*self.tree.get_children())
        parent = self.tree.insert("", "end", text=path, open=True, values=[path])
        for item in os.listdir(path):
            abspath = os.path.join(path, item)
            if os.path.isdir(abspath):
                self.tree.insert(parent, "end", text=item, open=False, values=[abspath])
            else:
                self.tree.insert(parent, "end", text=item, values=[abspath])

    def popup_menu(self, event):
        if self.tree.selection():
            self.context_menu.post(event.x_root, event.y_root)

    def search_files(self):
        query = simpledialog.askstring("Suche", "Suchbegriff eingeben:")
        if query:
            threading.Thread(target=self.perform_search, args=(query,)).start()

    def perform_search(self, query):
        try:
            schema = Schema(title=TEXT(stored=True), path=ID(stored=True))
            ix = index.create_in("indexdir", schema)
            writer = ix.writer()
            for root, _, files in os.walk(self.base_path):
                for file in files:
                    writer.add_document(title=file, path=os.path.join(root, file))
            writer.commit()

            with ix.searcher() as searcher:
                parser = QueryParser("title", ix.schema)
                myquery = parser.parse(query)
                results = searcher.search(myquery)
                for result in results:
                    print(result['title'], result['path'])
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler bei der Suche: {e}")

def main():
    lock_screen = LockScreen()
    lock_screen.mainloop()

if __name__ == "__main__":
    main()
