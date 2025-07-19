import tkinter as tk
from tkinter import ttk, messagebox
import threading
import subprocess
import time
import queue
import signal
import psutil
import os
import sys
import cv2
import logging

from .gui_config import *
from .gui_frames import AttendanceDataFrame
from .recognition_frame import RecognitionFrame
from .data_entry_frame import DataEntryFrame

class AttendanceGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self._setup_window()
        self._setup_variables()
        self._setup_ui()
        self._setup_web_app()

    def _setup_window(self):
        self.title('Hệ thống điểm danh khuôn mặt')
        self.geometry(f'{WINDOW_WIDTH}x{WINDOW_HEIGHT}')
        self.configure(bg=DARK_BG)
        self.resizable(False, False)

    def _setup_variables(self):
        # Quản lý webcam tập trung
        self.shared_cap = None
        self.webcam_device_id = None
        self.webcam_lock = threading.Lock()
        
        self.web_process = None
        self.web_running = False
        self.log_queue = queue.Queue()

        # Đăng ký signal handler để tắt hoàn toàn
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def _setup_ui(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TButton', font=('Arial', 16, 'bold'), padding=5, background=DARK_BTN, foreground=DARK_TEXT)
        style.map('TButton', background=[('active', DARK_BTN_HOVER)])
        style.configure('TCheckbutton', font=('Arial', 14), background=DARK_BG, foreground=DARK_TEXT, indicatorcolor=DARK_ACCENT, padding=5)
        
        title_frame = tk.Frame(self, bg=DARK_ACCENT, height=70)
        title_frame.pack(fill='x', side='top')
        title_label = tk.Label(title_frame, text='HỆ THỐNG ĐIỂM DANH KHUÔN MẶT', font=('Trebuchet MS', 22, 'bold'), fg='white', bg=DARK_ACCENT)
        title_label.pack(pady=2)

        container = tk.Frame(self, bg=DARK_BG)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        
        self.frames = {}
        frame_classes = {
            'RecognitionFrame': RecognitionFrame,
            'DataEntryFrame': DataEntryFrame, 
            'AttendanceDataFrame': AttendanceDataFrame
        }
        
        for frame_name, frame_class in frame_classes.items():
            frame = frame_class(container, self)
            self.frames[frame_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        # Manually raise the first frame without starting processes
        first_frame = self.frames['RecognitionFrame']
        first_frame.reset_state(log=False) # Set initial state correctly
        first_frame.tkraise()
        
        self.protocol("WM_DELETE_WINDOW", self.on_exit)
        self.update_log()
        
        self.attributes('-fullscreen', True)
        self.bind("<Escape>", lambda e: self.attributes("-fullscreen", False))

    def _setup_web_app(self):
        threading.Thread(target=self.start_web_app, daemon=True).start()

    def initialize_webcam(self):
        """Khởi tạo webcam tập trung"""
        with self.webcam_lock:
            if self.shared_cap is not None:
                return True  # Webcam đã được khởi tạo
                
            # Thử nhiều video device khác nhau
            video_devices = [0, 1, 2, 10, 20]
            
            for device_id in video_devices:
                try:
                    self.write_log(f'[WEBCAM] Đang thử mở webcam device {device_id}...')
                    cap = cv2.VideoCapture(device_id)
                    if cap.isOpened():
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        self.shared_cap = cap
                        self.webcam_device_id = device_id
                        self.write_log(f'Đã kết nối thành công với device {device_id}.')
                        return True
                    else:
                        cap.release()
                except Exception as e:
                    self.write_log(f'Lỗi với device {device_id}: {e}')
            
            self.write_log('Không thể mở webcam với bất kỳ device nào.')
            return False

    def get_webcam(self):
        """Lấy webcam đã được khởi tạo"""
        with self.webcam_lock:
            return self.shared_cap

    def release_webcam(self):
        """Giải phóng webcam"""
        with self.webcam_lock:
            if self.shared_cap:
                self.shared_cap.release()
                self.shared_cap = None
                self.webcam_device_id = None
                self.write_log('Đã giải phóng webcam.')

    def read_webcam_frame(self):
        """Đọc frame từ webcam"""
        with self.webcam_lock:
            if self.shared_cap and self.shared_cap.isOpened():
                return self.shared_cap.read()
            return False, None

    def show_frame(self, frame_name):
        # Dừng các tiến trình của frame cũ trước khi chuyển
        current_frame_key = next((key for key, value in self.frames.items() if value.winfo_ismapped()), None)
        if current_frame_key:
            current_frame_obj = self.frames[current_frame_key]
            if hasattr(current_frame_obj, 'stop_processes'):
                current_frame_obj.stop_processes()

        # Hiển thị frame mới
        frame = self.frames[frame_name]

        # Reset lại frame nhận diện khi quay lại
        if frame_name == 'RecognitionFrame':
            if hasattr(frame, 'reset_state'):
                frame.reset_state()

        frame.tkraise()
        
        # Bắt đầu tiến trình của frame mới
        if hasattr(frame, 'start_processes'):
            frame.start_processes()

    def write_log(self, msg):
        timestamp = time.strftime('%H:%M:%S')
        log_line = f'[{timestamp}] {msg}'
        self.log_queue.put(log_line)
        logging.info(msg)

    def update_log(self):
        try:
            while True: 
                msg = self.log_queue.get_nowait()
                if msg:
                    for frame in self.frames.values():
                        if frame.winfo_ismapped() and hasattr(frame, 'log_text'):
                            frame.log_text.config(state='normal')
                            frame.log_text.insert('end', msg + '\n')
                            frame.log_text.see('end')
                            frame.log_text.config(state='disabled')
        except queue.Empty:
            pass
        self.after(100, self.update_log)

    def start_web_app(self):
        if self.web_running:
            return
            
        try:
            self.write_log('Đang khởi động web app...')
            self.web_process = subprocess.Popen([
                sys.executable, 'web_app/app.py'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Chờ web app khởi động
            time.sleep(3)  # Chờ 3 giây để Flask start
            self.web_running = True
            self.write_log('Web app đã khởi động thành công.')
            
        except Exception as e:
            self.write_log(f'Lỗi khởi động web app: {e}')
            self.web_running = False

    def on_exit(self):
        self.write_log('Nhận được yêu cầu thoát. Đang dọn dẹp...')
        if messagebox.askokcancel("Thoát", "Bạn có chắc chắn muốn thoát chương trình?"):
            # Dừng tất cả các frame
            for frame in self.frames.values():
                 if hasattr(frame, 'stop_processes'):
                    frame.stop_processes()

            # Tắt web app một cách mạnh mẽ
            if self.web_process:
                self.write_log('Đang tắt tiến trình web app...')
                try:
                    # Thử terminate trước
                    self.web_process.terminate()
                    self.web_process.wait(timeout=3)
                    self.write_log('Web app đã được tắt thành công.')
                except subprocess.TimeoutExpired:
                    self.write_log('Web app không phản hồi, buộc dừng...')
                    try:
                        self.web_process.kill()
                        self.web_process.wait(timeout=2)
                    except:
                        pass
                
                # Đảm bảo tắt hoàn toàn bằng cách tìm và kill tất cả process liên quan
                try:
                    # Tìm tất cả process Python chạy web app
                    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                        try:
                            cmdline = proc.info['cmdline']
                            if cmdline and any('web_app/app.py' in arg for arg in cmdline):
                                self.write_log(f'Tìm thấy process web app PID {proc.info["pid"]}, đang tắt...')
                                proc.terminate()
                                proc.wait(timeout=2)
                        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                            pass
                except Exception as e:
                    self.write_log(f'Lỗi khi tìm process web app: {e}')
            
            # Tắt tất cả process ngrok nếu có
            try:
                subprocess.run(['ngrok', 'stop'], capture_output=True, timeout=5)
                self.write_log('Đã tắt ngrok.')
            except:
                pass
            
            self.web_running = False
            self.write_log('Đã dọn dẹp xong. Tạm biệt!')
            self.destroy()

    def signal_handler(self, signum, frame):
        """Xử lý signal từ hệ thống để tắt hoàn toàn"""
        self.write_log(f'Nhận signal {signum}, đang tắt ứng dụng...')
        self.force_exit()

    def force_exit(self):
        """Tắt ứng dụng một cách mạnh mẽ"""
        try:
            # Dừng tất cả các frame
            for frame in self.frames.values():
                 if hasattr(frame, 'stop_processes'):
                    frame.stop_processes()

            # Tắt web app
            if self.web_process:
                try:
                    self.web_process.terminate()
                    self.web_process.wait(timeout=2)
                except:
                    try:
                        self.web_process.kill()
                    except:
                        pass

            # Tìm và tắt tất cả process web app
            try:
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        cmdline = proc.info['cmdline']
                        if cmdline and any('web_app/app.py' in arg for arg in cmdline):
                            proc.terminate()
                            proc.wait(timeout=1)
                    except:
                        pass
            except:
                pass

            # Tắt ngrok
            try:
                subprocess.run(['ngrok', 'stop'], capture_output=True, timeout=3)
            except:
                pass

        except Exception as e:
            print(f"Lỗi khi tắt ứng dụng: {e}")
        finally:
            os._exit(0)

if __name__ == '__main__':
    if sys.platform.startswith('win'):
        import multiprocessing
        multiprocessing.freeze_support()
        
    app = AttendanceGUI()
    app.mainloop() 