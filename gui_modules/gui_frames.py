import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from PIL import Image, ImageTk
import cv2
import threading
import subprocess
import time
import requests
import os
import queue
import pandas as pd
import numpy as np
from datetime import datetime
import textwrap
import sqlite3

from .gui_config import *
from .gui_components import EnlargedFaceWindow, OnScreenKeyboardFrame
import sys
import os
# Thêm thư mục cha vào path để import các module khác
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.recognition_class import RecognitionSystem
from core.smart_tts import play_name_smart
from core.recognition_simple import RecognitionSimple

class AttendanceDataFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=DARK_BG)
        self.controller = controller
        self._setup_ui()
        self._setup_touch_support()

    def _setup_ui(self):
        # --- Layout ---
        title = tk.Label(self, text='DỮ LIỆU ĐIỂM DANH', font=('Trebuchet MS', 22, 'bold'), fg='white', bg=DARK_ACCENT)
        title.pack(fill='x', pady=(0, 5))

        # Bảng dữ liệu điểm danh
        data_frame = tk.Frame(self, bg=DARK_BG)
        data_frame.pack(fill='x', padx=10, pady=5)
        y_scrollbar = ttk.Scrollbar(data_frame, orient='vertical')
        self.attendance_display = tk.Text(
            data_frame,
            wrap="none",
            font=("Courier", 16),
            bg=DARK_PANEL,
            fg=DARK_TEXT,
            borderwidth=0,
            highlightthickness=0,
            height=15,
            yscrollcommand=y_scrollbar.set
        )
        self.attendance_display.tag_configure('bold_header', font=("Courier", 16, "bold"))
        y_scrollbar.config(command=self.attendance_display.yview)
        y_scrollbar.pack(side='right', fill='y')
        self.attendance_display.pack(fill="x", expand=False, padx=5, pady=5)
        self.attendance_display.config(state="disabled")

        # Nút điều khiển
        btn_frame = tk.Frame(self, bg=DARK_BG)
        btn_frame.pack(fill='x', pady=5)
        self.refresh_btn = ttk.Button(btn_frame, text='Làm mới', command=self.load_attendance_data)
        self.refresh_btn.pack(side='left', padx=10, ipadx=10, ipady=5)
        self.new_person_btn = ttk.Button(btn_frame, text='Thêm người mới', command=lambda: self.controller.show_frame('DataEntryFrame'))
        self.new_person_btn.pack(side='left', padx=10, ipadx=10, ipady=5)
        self.back_btn = ttk.Button(btn_frame, text='Quay lại nhận diện', command=self.switch_to_recognition)
        self.back_btn.pack(side='right', padx=10, ipadx=10, ipady=5)

        # Log hệ thống
        self.log_text = scrolledtext.ScrolledText(self, font=('Consolas', 12), height=4, state='disabled', bg='#23272f', fg=DARK_TEXT)
        self.log_text.pack(side='bottom', fill='x', padx=10, pady=5)

    def _setup_touch_support(self):
        # Hỗ trợ kéo bằng cảm ứng
        self.attendance_display.bind('<Button-1>', self.on_text_click)
        self.attendance_display.bind('<B1-Motion>', self.on_text_drag)
        self.attendance_display.bind('<ButtonRelease-1>', self.on_text_release)
        self.scroll_start_y = 0

        self.log_text.bind('<Button-1>', self._log_on_click)
        self.log_text.bind('<B1-Motion>', self._log_on_drag)
        self.log_text.bind('<ButtonRelease-1>', self._log_on_release)
        self._log_scroll_start_y = 0
        self._log_scroll_start_view = 0

    def start_processes(self):
        # Khởi tạo PIR monitoring cho cửa sổ này
        self.write_log("[PIR] Bắt đầu giám sát PIR ở cửa sổ xem dữ liệu (timeout: 2 phút)")
        self.load_attendance_data()

    def stop_processes(self):
        pass

    def write_log(self, msg):
        self.controller.write_log(msg)

    def update_log(self):
        try:
            while True:
                msg = self.controller.log_queue.get_nowait()
                if msg:
                    self.log_text.config(state='normal')
                    self.log_text.insert('end', msg + '\n')
                    self.log_text.see('end')
                    self.log_text.config(state='disabled')
        except queue.Empty:
            pass
        self.after(100, self.update_log)

    def load_attendance_data(self):
        self.write_log('Bắt đầu làm mới dữ liệu điểm danh...')
        if not self.controller.web_running:
            self.write_log(' Web app chưa sẵn sàng, sẽ thử lại sau...')
            self.after(3000, self.load_attendance_data)
            return
        
        def load_task():
            try:
                response = requests.get(API_ATTENDANCE_URL, timeout=10)
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if isinstance(data, list):
                            df = pd.DataFrame(data)
                            self.after(0, self.display_attendance_data, df)
                            self.write_log('Tải và hiển thị dữ liệu điểm danh thành công.')
                        else:
                            self.write_log(' Lỗi: Dữ liệu không đúng định dạng.')
                    except ValueError:
                        dfs = pd.read_html(response.text)
                        if dfs:
                            df = dfs[0]
                            self.after(0, self.display_attendance_data, df)
                            self.write_log('Tải và hiển thị dữ liệu điểm danh thành công.')
                        else:
                            self.write_log('Lỗi: Không tìm thấy bảng dữ liệu.')
                else:
                    self.write_log(f'Lỗi HTTP: {response.status_code}')
            except requests.exceptions.ConnectionError:
                self.write_log('Lỗi kết nối: Web app chưa sẵn sàng, sẽ thử lại sau...')
                self.after(3000, self.load_attendance_data)
            except Exception as e:
                self.write_log(f' Lỗi khi tải dữ liệu: {e}')
        
        threading.Thread(target=load_task, daemon=True).start()

    def display_attendance_data(self, df):
        if df.empty:
            self.write_log('Không có dữ liệu điểm danh.')
            return
        
        column_mapping = {
            'Lo\u1ea1i': 'Type', 'Ng\u00e0y/ gi\u1edd': 'Timestamp', 
            'Th\u00f4ng tin': 'Data', '\u0110\u1ed9 tin c\u1eady': 'Confidence',
            'Ngày/ giờ': 'Timestamp', 'Thông tin': 'Data', 'Loại': 'Type',
            'Độ tin cậy': 'Confidence', 'timestamp': 'Timestamp', 'data': 'Data',
            'type': 'Type', 'confidence': 'Confidence'
        }
        df = df.rename(columns=lambda c: column_mapping.get(c, c))
        required_cols = ['Timestamp', 'Data', 'Type', 'Confidence']
        for col in required_cols:
            if col not in df.columns:
                df[col] = ''
        df = df[required_cols]
        
        self.attendance_display.config(state="normal")
        self.attendance_display.delete("1.0", tk.END)
        header = "Ngày/giờ                              Thông tin                                                   Loại                 Độ tin cậy\n"
        self.attendance_display.insert(tk.END, header, 'bold_header')
        self.attendance_display.insert(tk.END, "\n")
        self.attendance_display.tag_configure('bold_header', font=("Arial", 16, "bold"))
        
        data_col_width = 30
        timestamp_padding = " " * 20
        for _, row in df.iterrows():
            timestamp = str(row.get('Timestamp', ''))
            data = str(row.get('Data', ''))
            record_type = str(row.get('Type', ''))
            confidence = row.get('Confidence', '')
            
            try:
                conf_val = float(confidence)
                confidence_str = f"{conf_val*100:.1f} %"
            except Exception:
                confidence_str = str(confidence)
            
            original_lines = data.splitlines()
            all_display_lines = []
            for line in original_lines:
                wrapped_lines = textwrap.wrap(line, width=data_col_width, replace_whitespace=False, drop_whitespace=False)
                if not wrapped_lines:
                    all_display_lines.append('')
                else:
                    all_display_lines.extend(wrapped_lines)
            if not all_display_lines:
                all_display_lines = ['']
            
            first_display_line = all_display_lines[0]
            line_to_print = f"{timestamp:<20} {first_display_line:<30} {record_type:<10} {confidence_str:<10}\n"
            self.attendance_display.insert(tk.END, line_to_print)
            
            if len(all_display_lines) > 1:
                for subsequent_line in all_display_lines[1:]:
                    padding_end = " " * (10 + 10 + 2)
                    indented_line = f"{timestamp_padding} {subsequent_line:<30}{padding_end}\n"
                    self.attendance_display.insert(tk.END, indented_line)
        
        self.attendance_display.config(state="disabled")

    def on_text_click(self, event):
        self.scroll_start_y = event.y
        self.scroll_start_view = self.attendance_display.yview()[0]

    def on_text_drag(self, event):
        if hasattr(self, 'scroll_start_y') and hasattr(self, 'scroll_start_view'):
            delta_y = self.scroll_start_y - event.y
            scroll_amount = delta_y / 100 
            self.attendance_display.yview_scroll(int(scroll_amount), "units")

    def on_text_release(self, event):
        self.scroll_start_y = None
        self.scroll_start_view = None

    def _log_on_click(self, event):
        self._log_scroll_start_y = event.y
        self._log_scroll_start_view = self.log_text.yview()[0]

    def _log_on_drag(self, event):
        if hasattr(self, '_log_scroll_start_y') and hasattr(self, '_log_scroll_start_view'):
            delta_y = self._log_scroll_start_y - event.y
            scroll_amount = delta_y / 40
            self.log_text.yview_scroll(int(scroll_amount), "units")

    def _log_on_release(self, event):
        self._log_scroll_start_y = None
        self._log_scroll_start_view = None

    def switch_to_recognition(self):
        self.stop_processes()
        self.controller.show_frame('RecognitionFrame')

# Import các frame khác để tránh circular import
# Các frame được import trong gui_main.py và truyền qua controller 
from .recognition_frame import RecognitionFrame
from .data_entry_frame import DataEntryFrame 