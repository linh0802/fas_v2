import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import cv2
from .gui_config import DARK_PANEL, DARK_ACCENT, DARK_TEXT, DARK_BTN

class EnlargedFaceWindow(tk.Toplevel):
    def __init__(self, parent, name, image):
        super().__init__(parent)
        self.title(f"Khuôn mặt: {name}")
        self.configure(bg=DARK_PANEL)
        self.image_reference = None # Thuộc tính để giữ tham chiếu ảnh

        # Lấy kích thước màn hình
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        w, h = img.size
        # Phóng to nhưng không vượt quá màn hình (trừ lề 100px)
        max_w = screen_w - 100
        max_h = screen_h - 100
        scale = min(max_w / w, max_h / h, 4)  # Không phóng quá 4 lần, và không vượt màn hình
        new_w, new_h = int(w * scale), int(h * scale)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        imgtk = ImageTk.PhotoImage(image=img)
        self.image_reference = imgtk # Giữ tham chiếu

        label = tk.Label(self, image=self.image_reference, bg=DARK_PANEL)
        label.pack(padx=20, pady=20)
        
        self.transient(parent)
        try:
            self.grab_set()
        except tk.TclError:
            pass  # Bỏ qua lỗi grab nếu window không viewable

class OnScreenKeyboardFrame(tk.Frame):
    def __init__(self, parent, entry_widget, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.entry_widget = entry_widget
        self.configure(bg='#23272f')
        keys = [
            ['1','2','3','4','5','6','7','8','9','0','-'],
            ['q','w','e','r','t','y','u','i','o','p','_'],
            ['a','s','d','f','g','h','j','k','l'],
            ['z','x','c','v','b','n','m','.','@'],
        ]
        # Vẽ các nút ký tự
        for r, row in enumerate(keys):
            for c, key in enumerate(row):
                btn = tk.Button(self, text=key, width=3, height=2, command=lambda k=key: self._insert(k), bg='#222c36', fg='white', font=('Arial', 11))
                btn.grid(row=r, column=c, padx=1, pady=1)
        # Nút ⌫ ở cuối dòng 3, chiếm 2 dòng (rowspan=2)
        backspace_btn = tk.Button(self, text='⌫', width=3, height=5, command=self._backspace, bg='#d32f2f', fg='white', font=('Arial', 13, 'bold'))
        backspace_btn.grid(row=2, column=len(keys[2]), rowspan=2, sticky='ns', padx=2, pady=1)
        # Hàng cuối: Space và Đóng
        space_btn = tk.Button(self, text='Space', command=lambda: self._insert(' '), bg='#222c36', fg='white', font=('Arial', 11))
        space_btn.grid(row=4, column=0, columnspan=6, padx=1, pady=1, sticky='we')
        close_btn = tk.Button(self, text='Đóng', command=self.hide, bg='#00bcd4', fg='white', font=('Arial', 11, 'bold'))
        close_btn.grid(row=4, column=6, columnspan=3, padx=1, pady=1, sticky='we')
    
    def _insert(self, char):
        self.entry_widget.insert(tk.INSERT, char)
        self.entry_widget.focus_set()
    
    def _backspace(self):
        current = self.entry_widget.get()
        pos = self.entry_widget.index(tk.INSERT)
        if pos > 0:
            new = current[:pos-1] + current[pos:]
            self.entry_widget.delete(0, tk.END)
            self.entry_widget.insert(0, new)
            self.entry_widget.icursor(pos-1)
        self.entry_widget.focus_set()
    
    def hide(self):
        self.place_forget() 