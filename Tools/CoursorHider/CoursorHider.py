import tkinter as tk
import keyboard
import threading
import sys

class CursorController:
    def __init__(self, root):
        self.root = root
        self.root.title("Управление курсором")
        self.root.geometry("250x210")
        self.root.resizable(False, False)
        self.overlay = None
        self.create_widgets()
        self.setup_hotkeys()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)

        self.hide_button = tk.Button(button_frame,
                                     text="Скрыть курсор",
                                     command=self.hide_cursor_global,
                                     bg="#e74c3c",
                                     fg="white",
                                     font=("Arial", 11, "bold"),
                                     width=18,
                                     height=2,
                                     relief=tk.RAISED,
                                     bd=3)
        self.hide_button.pack(pady=5)

        self.show_button = tk.Button(button_frame,
                                     text="Показать курсор",
                                     command=self.show_cursor_global,
                                     bg="#27ae60",
                                     fg="white",
                                     font=("Arial", 11, "bold"),
                                     width=18,
                                     height=2,
                                     relief=tk.RAISED,
                                     bd=3)
        self.show_button.pack(pady=5)

        info_frame = tk.Frame(self.root, bg="#ecf0f1", relief=tk.GROOVE, bd=2)
        info_frame.pack(pady=5, padx=15, fill=tk.BOTH)

        hotkeys = [
            "Ctrl + Alt + H - Скрыть курсор",
            "Ctrl + Alt + S - Показать курсор",
        ]

        for hotkey in hotkeys:
            tk.Label(info_frame,
                     text=hotkey,
                     font=("Arial", 9),
                     bg="#ecf0f1",
                     fg="#7f8c8d").pack()

    def hide_cursor_global(self):
        try:
            if self.overlay is not None:
                try:
                    self.overlay.destroy()
                except:
                    pass

            self.overlay = tk.Toplevel(self.root)
            self.overlay.attributes('-fullscreen', True)
            self.overlay.attributes('-topmost', True)
            self.overlay.attributes('-alpha', 0.01)
            self.overlay.configure(bg='black')
            self.overlay.overrideredirect(True)
            self.overlay.config(cursor="none")
            self.overlay.bind('<Escape>', lambda e: self.show_cursor_global())
        except Exception:
            pass

    def show_cursor_global(self):
        try:
            if self.overlay is not None:
                self.overlay.destroy()
                self.overlay = None
        except Exception:
            pass

    def setup_hotkeys(self):
        try:
            keyboard.add_hotkey('ctrl+alt+h', self.hide_cursor_global)
            keyboard.add_hotkey('ctrl+alt+s', self.show_cursor_global)
            self.keyboard_thread = threading.Thread(target=self.keyboard_listener, daemon=True)
            self.keyboard_thread.start()
        except Exception:
            pass

    def keyboard_listener(self):
        keyboard.wait()

    def on_closing(self):
        self.show_cursor_global()
        try:
            keyboard.remove_hotkey('ctrl+alt+h')
            keyboard.remove_hotkey('ctrl+alt+s')
        except:
            pass
        self.root.destroy()
        sys.exit(0)

def main():
    root = tk.Tk()
    app = CursorController(root)
    root.mainloop()

if __name__ == "__main__":
    main()