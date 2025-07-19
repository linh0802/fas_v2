import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from PIL import Image, ImageTk
import cv2
import threading
import time
import queue
import numpy as np
from datetime import datetime
import gc
import os
import psutil

from .gui_config import *
from .gui_components import EnlargedFaceWindow
import sys
import os
# Thêm thư mục cha vào path để import các module khác
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.recognition_class import RecognitionSystem
from core.smart_tts import play_name_smart
from core.recognition_simple import RecognitionSimple

class RecognitionFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=DARK_BG)
        self.controller = controller
        self._setup_ui()
        self._setup_variables()
        self._setup_touch_support()
        self.reset_state(log=False)
        # Thêm label hiển thị CPU/RAM
        self.sysinfo_label = tk.Label(self, text="", font=("Arial", 8), fg="#AAA", bg=DARK_BG)
        self.sysinfo_label.place(relx=1.0, rely=1.0, anchor="se", x=-8, y=-8)
        self._update_sysinfo()

    def _setup_ui(self):
        # --- Main layout ---
        main_frame = tk.Frame(self, bg=DARK_BG)
        main_frame.pack(side='top', fill='both', expand=False, padx=5, pady=2)
        
        # --- Webcam ---
        webcam_frame = tk.LabelFrame(main_frame, text='Webcam', font=('Arial', 16, 'bold'), bg=DARK_PANEL, fg=DARK_ACCENT, relief='groove', bd=1, labelanchor='n', width=640, height=480)
        webcam_frame.pack(side='left')
        webcam_frame.pack_propagate(False)
        self.webcam_status_var = tk.StringVar(value='Hệ thống đang tắt')
        self.webcam_status_label = tk.Label(
            webcam_frame,
            textvariable=self.webcam_status_var, 
            font=('Arial', 16, 'bold'), 
            fg=DARK_ACCENT, 
            bg=DARK_PANEL)
        self.webcam_status_label.pack(side='bottom', fill='x', pady=(1, 1))
        self.video_label = tk.Label(webcam_frame, bg='#11151c', width=640, height=480)
        self.video_label.pack(expand=True, fill='both', side='top')

        # --- Cột phải ---
        right_col = tk.Frame(main_frame, bg=DARK_BG, width=380, height=480)
        right_col.pack(side='left')
        right_col.pack_propagate(False)
        
        # --- Khuôn mặt đã nhận diện (trên) ---
        faces_frame = tk.LabelFrame(right_col, text='Khuôn mặt đã nhận diện', font=('Arial', 16, 'bold'), bg=DARK_PANEL, fg=DARK_ACCENT, relief='groove', bd=1, labelanchor='n', height=360)
        faces_frame.pack(side='top', fill='x')
        faces_frame.pack_propagate(False)
        
        faces_canvas_frame = tk.Frame(faces_frame, bg=DARK_PANEL)
        faces_canvas_frame.pack(fill='both', expand=True)
        self.faces_canvas = tk.Canvas(faces_canvas_frame, bg=DARK_PANEL, highlightthickness=0, height=340)
        self.faces_canvas.pack(side='left', fill='both', expand=True)
        faces_scrollbar = ttk.Scrollbar(faces_canvas_frame, orient='vertical', command=self.faces_canvas.yview)
        faces_scrollbar.pack(side='right', fill='y')
        self.faces_canvas.configure(yscrollcommand=faces_scrollbar.set)
        
        # --- Log (dưới cùng cột phải) ---
        log_frame = tk.Frame(right_col, bg=DARK_BG, height=120)
        log_frame.pack(side='bottom', fill='x')
        log_frame.pack_propagate(False)
        self.log_text = scrolledtext.ScrolledText(log_frame, font=('Consolas', 12), height=4, state='disabled', bg='#23272f', fg=DARK_TEXT)
        self.log_text.pack(side='bottom', fill='both', expand=True)
        
        # --- Nút điều khiển webcam (dưới cùng, kéo dài toàn bộ chiều ngang) ---
        webcam_btn_frame = tk.Frame(self, bg=DARK_BG)
        webcam_btn_frame.pack(side='bottom', fill='x', pady=(0, 10))
        for i in range(6):
            webcam_btn_frame.grid_columnconfigure(i, weight=1)
        
        self.start_btn = ttk.Button(webcam_btn_frame, text='Khởi động', command=self.start_recognition_system)
        self.start_btn.grid(row=0, column=0, padx=2, ipadx=2, ipady=2)
        self.stop_btn = ttk.Button(webcam_btn_frame, text='Tạm dừng', command=self.stop_recognition_system, state='disabled')
        self.stop_btn.grid(row=0, column=1, padx=2, ipadx=2, ipady=2)
        self.new_person_btn = ttk.Button(webcam_btn_frame, text='Thêm người mới', command=self.switch_to_data_entry)
        self.new_person_btn.grid(row=0, column=2, padx=2, ipadx=2, ipady=2)
        self.attendance_data_btn = ttk.Button(webcam_btn_frame, text='Dữ liệu điểm danh', command=lambda: self.controller.show_frame('AttendanceDataFrame'))
        self.attendance_data_btn.grid(row=0, column=3, padx=2, ipadx=2, ipady=2)
        self.exit_btn = ttk.Button(webcam_btn_frame, text='Thoát', command=self.controller.on_exit)
        self.exit_btn.grid(row=0, column=4, padx=2, ipadx=2, ipady=2)
        self.verbose_logging = tk.BooleanVar(value=False)
        self.verbose_log_check = ttk.Checkbutton(webcam_btn_frame, text='Log chi tiết', variable=self.verbose_logging, command=self.toggle_verbose_log, style='Verbose.TCheckbutton')
        self.verbose_log_check.grid(row=0, column=5, padx=2)

    def _setup_variables(self):
        self.recognition_system = None
        self.webcam_thread = None
        self.recognition_thread = None
        self.running = False
        self.pir_sensor = None
        self.face_thumbs = []
        self.original_faces = {}
        self.recognized_names = set()
        self.recognized_faces = []
        self.pir_last_motion_time = 0
        self.pir_idle = True
        self.pir_timeout = 30
        self.fps = 0
        self._fps_frame_count = 0
        self._fps_start_time = time.time()
        self._image_references = {}
        self.frame_queue = queue.Queue(maxsize=2)
        self.pir_wait_announced = False
        
        # Hàng đợi mới cho xử lý đa luồng
        self.recognition_results_queue = queue.Queue(maxsize=5)
        self.tts_queue = queue.Queue(maxsize=3)

        self.qr_capture_popup = None
        self.qr_capture_in_progress = False
        self.recog_simple = RecognitionSimple(model_path="models/train_FN.h5")
        self.detected_name = None
        self.detected_confidence = 0

    def _setup_touch_support(self):
        # Hỗ trợ cuộn cảm ứng
        self.faces_canvas.bind('<Button-1>', self._faces_canvas_on_click)
        self.faces_canvas.bind('<B1-Motion>', self._faces_canvas_on_drag)
        self.faces_canvas.bind('<ButtonRelease-1>', self._faces_canvas_on_release)
        self._faces_scroll_start_y = 0
        self._faces_scroll_start_view = 0

        self.log_text.bind('<Button-1>', self._log_on_click)
        self.log_text.bind('<B1-Motion>', self._log_on_drag)
        self.log_text.bind('<ButtonRelease-1>', self._log_on_release)
        self._log_scroll_start_y = 0
        self._log_scroll_start_view = 0

    def switch_to_data_entry(self):
        """Chuyển sang màn hình thêm người mới và dừng hệ thống nhận diện"""
        if self.running:
            self.write_log("[CHUYỂN] Dừng hệ thống nhận diện để chuyển sang thêm người mới...")
            self.stop_recognition_system()
        self.controller.show_frame('DataEntryFrame')

    def reset_state(self, log=True):
        self.stop_recognition_system()
        
        self.face_thumbs.clear()
        self.original_faces.clear()
        self.recognized_names.clear()
        self.recognized_faces.clear()
        
        self.pir_last_motion_time = 0
        self.pir_idle = True
        self.fps = 0
        self.scroll_start_y = 0
        self._fps_frame_count = 0
        self._fps_start_time = time.time()
        
        self.webcam_status_var.set('Hệ thống sẵn sàng. Nhấn "Khởi động" để bắt đầu.')
        self.faces_canvas.delete('all')
        
        # Xóa hình ảnh webcam và hiển thị frame trống
        idle_frame = self.get_idle_frame()
        img = Image.fromarray(cv2.cvtColor(idle_frame, cv2.COLOR_BGR2RGB))
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.config(image=imgtk)
        self._image_references['video_label'] = imgtk
        
        # Xóa mọi image reference khác để tránh giữ ảnh cũ
        for k in list(self._image_references.keys()):
            if k != 'video_label':
                del self._image_references[k]
        
        # Reset trạng thái nút
        self.start_btn.config(state='normal', text='Khởi động')
        self.stop_btn.config(state='disabled')
        
        if log:
            self.write_log("Hệ thống nhận diện đã được reset.")

    def stop_processes(self):
        if self.running:
            self.stop_recognition_system()

    def stop_recognition_system(self):
        if not self.running and self.recognition_system is None:
            return
        self.write_log("Dừng hệ thống nhận diện...")
        self.running = False
        
        # Dừng các luồng
        if self.webcam_thread and self.webcam_thread.is_alive():
            self.webcam_thread.join(timeout=1)
        if self.recognition_thread and self.recognition_thread.is_alive():
            self.recognition_thread.join(timeout=1)
        if hasattr(self, 'tts_thread') and self.tts_thread and self.tts_thread.is_alive():
            self.tts_thread.join(timeout=1)
        
        # Dừng recognition system
        if self.recognition_system:
            if hasattr(self.recognition_system, 'stop'):
                self.recognition_system.stop()
            del self.recognition_system
            self.recognition_system = None
            gc.collect()
        
        # Giải phóng PIR sensor nếu có
        if self.pir_sensor:
            try:
                self.pir_sensor.release()
            except Exception as e:
                self.write_log(f"Lỗi khi giải phóng PIR: {e}")
            self.pir_sensor = None
        
        self.start_btn.config(state='normal', text='Khởi động lại')
        self.stop_btn.config(state='disabled')
        self.webcam_status_var.set('Hệ thống đã dừng.')
        self.controller.release_webcam()
        
        idle_frame = self.get_idle_frame()
        img = Image.fromarray(cv2.cvtColor(idle_frame, cv2.COLOR_BGR2RGB))
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.config(image=imgtk)
        self._image_references['video_label'] = imgtk
        for k in list(self._image_references.keys()):
            if k != 'video_label':
                del self._image_references[k]
        time.sleep(0.5)

    def write_log(self, msg):
        self.controller.write_log(msg)

    def start_recognition_system(self):
        """This is now the main entry point to start the system via the button."""
        if self.running:
            self.write_log('(!) Hệ thống nhận diện đã chạy từ trước.')
            return
        if not self.controller.web_running:
            self.write_log('Web app chưa khởi động xong, vui lòng đợi...')
            self.webcam_status_var.set('Đang chờ web app khởi động...')
            # Thử lại sau 1 giây
            self.after(1000, self.start_recognition_system)
            return
        self.write_log('=>Khởi động hệ thống nhận diện...')
        self.webcam_status_var.set('Đang khởi tạo các thành phần...')
        threading.Thread(target=self._initialize_system, daemon=True).start()

    def _initialize_system(self):
        try:
            # Nếu đã có pir_sensor cũ thì giải phóng trước khi tạo mới
            if self.pir_sensor:
                try:
                    self.pir_sensor.release()
                except Exception as e:
                    self.write_log(f"Lỗi khi giải phóng PIR cũ: {e}")
                self.pir_sensor = None
            
            # Khởi tạo RecognitionSystem với try-catch riêng
            try:
                self.recognition_system = RecognitionSystem(gui_log_func=self.write_log)
                self.recognition_system.attendance_callback = self.handle_callback
                self.pir_sensor = self.recognition_system.pir_sensor if hasattr(self.recognition_system, 'pir_sensor') else None
                self.write_log('=>Khởi tạo model và cảm biến thành công.')
                self.model_ready = True
            except Exception as e:
                self.write_log(f"=>Lỗi khởi tạo RecognitionSystem: {e}")
                self.webcam_status_var.set('Lỗi khởi tạo model.')
                self.start_btn.config(state='normal', text='Khởi động lại')
                self.stop_btn.config(state='disabled')
                self.model_ready = False
                return
            
            # Khởi tạo webcam với try-catch riêng
            try:
                if not self.controller.initialize_webcam():
                    self.write_log('=>Không thể mở webcam.')
                    self.webcam_status_var.set('Lỗi webcam.')
                    self.start_btn.config(state='normal', text='Khởi động lại')
                    self.stop_btn.config(state='disabled')
                    return
            except Exception as e:
                self.write_log(f"=>Lỗi khởi tạo webcam: {e}")
                self.webcam_status_var.set('Lỗi webcam.')
                self.start_btn.config(state='normal', text='Khởi động lại')
                self.stop_btn.config(state='disabled')
                return
            
            # Khởi tạo các thread
            try:
                self.running = True
                self.pir_last_motion_time = time.time()
                self.pir_idle = False
                self.webcam_status_var.set('Hệ thống đang nhận diện')
                self.webcam_thread = threading.Thread(target=self.update_webcam, daemon=True)
                self.recognition_thread = threading.Thread(target=self.recognition_processing_thread, daemon=True)
                self.tts_thread = threading.Thread(target=self.tts_processing_thread, daemon=True)
                self.webcam_thread.start()
                self.recognition_thread.start()
                self.tts_thread.start()
                self.update_gui_from_queue()
                self.start_btn.config(state='disabled', text='Khởi động lại')
                self.stop_btn.config(state='normal')
                self.webcam_status_var.set('Hệ thống đang hoạt động')
                self.write_log("=>Hệ thống nhận diện đã sẵn sàng.")
            except Exception as e:
                self.write_log(f"=>Lỗi khởi tạo thread: {e}")
                self.running = False
                self.webcam_status_var.set('Lỗi khởi tạo thread.')
                self.start_btn.config(state='normal', text='Khởi động lại')
                self.stop_btn.config(state='disabled')
        except Exception as e:
            self.write_log(f"=>Lỗi nghiêm trọng khi khởi tạo: {e}")
            self.webcam_status_var.set('Lỗi khởi tạo hệ thống.')
            self.start_btn.config(state='normal', text='Khởi động lại')
            self.stop_btn.config(state='disabled')

    def update_gui_from_queue(self):
        # Cập nhật video feed
        try:
            processed_frame = self.frame_queue.get_nowait()
            img = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
            img_resized = Image.fromarray(img).resize((640, 480), Image.Resampling.LANCZOS)
            imgtk = ImageTk.PhotoImage(image=img_resized)
            self._image_references['video_label'] = imgtk
            self.video_label.config(image=imgtk)
        except queue.Empty:
            pass

        # Cập nhật kết quả nhận diện
        try:
            (new_names, new_faces_imgs) = self.recognition_results_queue.get_nowait()
            if new_names:
                self.update_recognized_faces(new_names, new_faces_imgs)
        except queue.Empty:
            pass
        
        if self.running:
            self.after(30, self.update_gui_from_queue)

    def update_webcam(self):
        while self.running:
            # Luồng này chỉ đọc frame và đưa vào hàng đợi để xử lý
            now = time.time()
            is_motion = False # Mặc định là không có chuyển động
            if self.pir_sensor:
                try:
                    # Logic đọc PIR sensor trực tiếp hơn
                    is_motion = self.pir_sensor.is_motion()
                except Exception as e:
                    self.write_log(f"Lỗi đọc cảm biến: {e}")
                    is_motion = False 
            else:
                is_motion = True

            if is_motion:
                self.pir_last_motion_time = now
                if self.pir_idle:
                    self.write_log("Phát hiện chuyển động! Khởi động lại webcam...")
                    self.pir_idle = False
                    self.webcam_status_var.set('Hệ thống đang nhận diện')
                    # Reset flag khi có chuyển động
                    self.pir_wait_announced = False
                    if not self.controller.get_webcam():
                        self.controller.initialize_webcam()
            else:
                if not self.pir_idle and (now - self.pir_last_motion_time > self.pir_timeout):
                    self.pir_idle = True
                    self.webcam_status_var.set('Đang chờ tín hiệu PIR...')
                    self.controller.release_webcam()
                    self.write_log("Webcam đã tạm dừng.")
                    # Phát âm thông báo khi chuyển sang trạng thái chờ PIR, chỉ phát một lần
                    if not self.pir_wait_announced:
                        try:
                            # Gọi TTS trong main thread để tránh deadlock
                            self.after(0, lambda: self._play_pir_wait_message())
                        except Exception as e:
                            self.write_log(f"Lỗi khi phát âm thông báo PIR: {e}")
                        self.pir_wait_announced = True

            if self.pir_idle:
                idle_frame = self.get_idle_frame()
                try:
                    self.frame_queue.put_nowait(idle_frame)
                except queue.Full: pass
                time.sleep(0.5)
                continue
            
            if not self.controller.get_webcam():
                if not self.controller.initialize_webcam():
                    time.sleep(1)
                    continue

            ret, frame = self.controller.read_webcam_frame()
            if not ret: 
                time.sleep(0.1)
                continue
            
            # Cập nhật FPS và hiển thị frame ngay lập tức để giữ độ mượt
            self._fps_frame_count += 1
            elapsed = time.time() - self._fps_start_time
            if elapsed >= 1.0:
                self.fps = self._fps_frame_count / elapsed
                self._fps_frame_count = 0
                self._fps_start_time = time.time()
            
            display_frame = frame.copy()
            cv2.putText(display_frame, f"FPS: {self.fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            try:
                self.frame_queue.put_nowait(display_frame)
            except queue.Full: pass
            
            # Đưa frame vào hàng đợi để luồng nhận diện xử lý
            try:
                # Tạo một hàng đợi riêng cho việc xử lý AI
                pass # Sẽ được xử lý ở luồng khác
            except queue.Full:
                pass

    def recognition_processing_thread(self):
        """Luồng riêng chỉ để xử lý AI"""
        while self.running:
            if self.pir_idle or not getattr(self, 'model_ready', False):
                time.sleep(0.1)
                continue

            ret, frame = self.controller.read_webcam_frame()
            if not ret:
                time.sleep(0.1)
                continue
            
            # Xử lý AI trên mỗi frame đọc được
            processed_frame, new_names, new_faces_imgs = self.process_and_draw(frame)
            
            if new_names:
                try:
                    self.recognition_results_queue.put_nowait((new_names, new_faces_imgs))
                except queue.Full:
                    pass
            
            # Giảm tải một chút để tránh 100% CPU
            time.sleep(0.01)

    def toggle_verbose_log(self):
        """Bật/tắt chế độ log chi tiết."""
        state = "BẬT" if self.verbose_logging.get() else "TẮT"
        self.write_log(f"Chế độ log chi tiết đã được {state}.")

    def write_log_verbose(self, msg):
        """Ghi log chỉ khi chế độ verbose được bật."""
        if self.verbose_logging.get():
            self.controller.write_log(f"   [VERBOSE] {msg}")

    def _play_pir_wait_message(self):
        """Phát âm thông báo PIR thông qua queue"""
        try:
            self.tts_queue.put_nowait("Hệ thống tạm ngưng, đang chờ chuyển động")
        except queue.Full:
            pass  # Bỏ qua nếu queue đầy
        except Exception as e:
            self.write_log(f"Lỗi khi gửi thông báo PIR: {e}")

    def tts_processing_thread(self):
        """Thread riêng để xử lý TTS"""
        while self.running:
            try:
                message = self.tts_queue.get(timeout=1)
                if message:
                    play_name_smart(message, log_func=self.write_log)
            except queue.Empty:
                continue
            except Exception as e:
                self.write_log(f"Lỗi TTS: {e}")

    def process_and_draw(self, frame):
        if not self.recognition_system: return frame, set(), dict()
        
        self.write_log_verbose("Gọi recognition_system.detect_and_recognize...")
        faces, qr_codes = self.recognition_system.detect_and_recognize(frame)
        self.write_log_verbose(f"Kết quả: {len(faces)} khuôn mặt, {len(qr_codes)} QR.")

        new_names, new_faces_imgs = set(), dict()

        if not faces:
            self.write_log_verbose("Không phát hiện khuôn mặt nào trong frame.")

        for face in faces:
            name = face['name']
            confidence = face.get('confidence', 0)
            
            if name == "Fake":
                self.write_log(f"Phát hiện khuôn mặt giả (Conf: {confidence:.2f})")
            elif name == "Unknown":
                self.write_log(f"Khuôn mặt không xác định (Conf: {confidence:.2f})")
            elif name not in self.recognized_names:
                self.write_log(f"Thành công: {name} (Conf: {confidence:.2f})")
                new_names.add(name)
                x, y, w, h = face['facial_area']['x'], face['facial_area']['y'], face['facial_area']['w'], face['facial_area']['h']
                new_faces_imgs[name] = {
                    'img': frame[y:y+h, x:x+w],
                    'confidence': confidence
                }
            else:
                self.write_log_verbose(f"Đã nhận diện '{name}' trước đó, bỏ qua log chính.")

        return frame, new_names, new_faces_imgs

    def update_recognized_faces(self, new_names, new_faces_imgs):
        has_new_face = False
        for name in new_names:
            if name not in self.recognized_names:
                has_new_face = True
                self.recognized_names.add(name)
                face_data = new_faces_imgs[name]
                original_img = face_data['img']
                confidence = face_data['confidence']
                timestamp = datetime.now().strftime('%H:%M:%S')
                self.recognized_faces.insert(0, {
                    'img': cv2.resize(original_img, (90, 90)),
                    'name': name,
                    'timestamp': timestamp,
                    'confidence': confidence
                })
                self.original_faces[name] = original_img
        if has_new_face:
            self.recognized_faces = self.recognized_faces[:20]  # Cho phép nhiều hơn để cuộn
            self.faces_canvas.delete('all')
            self.face_thumbs.clear()
            y_offset = 4
            thumb_max_w = thumb_max_h = 90  # Thumbnail vuông 90x90
            for idx, photo in enumerate(self.recognized_faces):
                face_frame = tk.Frame(self.faces_canvas, bg=DARK_PANEL, height=thumb_max_h)
                self.faces_canvas.create_window(50, y_offset, window=face_frame, anchor='nw', width=280, height=thumb_max_h)
                # Resize trực tiếp về 90x90, không padding
                img = photo['img']
                img_resized = cv2.resize(img, (thumb_max_w, thumb_max_h), interpolation=cv2.INTER_AREA)
                imgtk = ImageTk.PhotoImage(image=Image.fromarray(cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)))
                self.face_thumbs.append(imgtk)
                img_label = tk.Label(face_frame, image=imgtk, bg=DARK_PANEL)
                img_label.pack(side='left', padx=0, pady=2)
                info_frame = tk.Frame(face_frame, bg=DARK_PANEL)
                info_frame.pack(side='left', fill='y', expand=True, padx=0)
                name_label = tk.Label(info_frame, text=photo['name'], font=('Arial', 15, 'bold'), fg=DARK_ACCENT, bg=DARK_PANEL, anchor='w')
                name_label.pack(fill='x', pady=(0, 1))
                time_label = tk.Label(info_frame, text=f"Thời gian: {photo['timestamp']}", font=('Arial', 13), fg=DARK_TEXT, bg=DARK_PANEL, anchor='w')
                time_label.pack(fill='x', pady=(0, 0))
                conf_label = tk.Label(info_frame, text=f"Độ tin cậy: {photo['confidence']*100:.2f} %", font=('Arial', 13), fg=DARK_TEXT, bg=DARK_PANEL, anchor='w')
                conf_label.pack(fill='x')
                callback = lambda e, n=photo['name'], i=self.original_faces[photo['name']]: self.show_enlarged_face(n, i)
                self.bind_all_children(face_frame, "<Button-1>", callback)
                y_offset += thumb_max_h + 2  # Các hàng sát nhau hơn
            # Cập nhật scrollregion
            total_height = max(180, y_offset)
            self.faces_canvas.config(scrollregion=(0, 0, 210, total_height))

    def show_enlarged_face(self, name, image):
        """Hiển thị cửa sổ phóng to ảnh."""
        if name in self.original_faces:
            window = EnlargedFaceWindow(self, name, image)
            self.wait_window(window)

    def bind_all_children(self, widget, event, callback):
        """Gán một event cho widget và tất cả các widget con của nó."""
        widget.bind(event, callback)
        for child in widget.winfo_children():
            self.bind_all_children(child, event, callback)

    def get_idle_frame(self):
        return np.zeros((480, 640, 3), dtype=np.uint8)

    def _faces_canvas_on_click(self, event):
        self._faces_scroll_start_y = event.y
        self._faces_scroll_start_view = self.faces_canvas.yview()[0]
    
    def _faces_canvas_on_drag(self, event):
        if hasattr(self, '_faces_scroll_start_y') and hasattr(self, '_faces_scroll_start_view'):
            delta_y = self._faces_scroll_start_y - event.y
            scroll_amount = delta_y / 40  # Giảm nhạy, cuộn chậm hơn
            self.faces_canvas.yview_scroll(int(scroll_amount), "units")
    
    def _faces_canvas_on_release(self, event):
        self._faces_scroll_start_y = None
        self._faces_scroll_start_view = None

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

    def handle_callback(self, data):
        """
        Xử lý callback từ RecognitionSystem (ví dụ: yêu cầu xác nhận QR capture)
        """
        if isinstance(data, dict) and data.get('type') == 'QR-CAPTURE-REQUEST':
            qr_data = data.get('qr_data')
            # Hiện popup xác nhận ở giữa cửa sổ nhận diện
            if self.qr_capture_in_progress:
                return  # Đang có popup, không hiện thêm
            self.qr_capture_in_progress = True
            self.show_qr_capture_popup(qr_data)

    def show_qr_capture_popup(self, qr_data):
        if self.qr_capture_popup:
            self.qr_capture_popup.destroy()
        self.qr_capture_popup = tk.Toplevel(self)
        self.qr_capture_popup.title("Xác nhận lưu ảnh QR")
        self.qr_capture_popup.geometry("400x180")
        self.qr_capture_popup.transient(self.controller)
        self.qr_capture_popup.grab_set()
        self.qr_capture_popup.configure(bg=DARK_PANEL)
        self.qr_capture_popup.resizable(False, False)
        # Đặt popup ở giữa cửa sổ nhận diện
        self.qr_capture_popup.update_idletasks()
        x = self.winfo_rootx() + self.winfo_width() // 2 - 200
        y = self.winfo_rooty() + self.winfo_height() // 2 - 90
        self.qr_capture_popup.geometry(f"400x180+{x}+{y}")
        label = tk.Label(self.qr_capture_popup, text="Bạn cần lưu ảnh khuôn mặt lên hệ thống để hoàn tất\nquá trình điểm danh bằng mã QR.", font=("Arial", 13), fg=DARK_ACCENT, bg=DARK_PANEL, wraplength=380)
        label.pack(pady=(30, 10))
        btn = ttk.Button(self.qr_capture_popup, text="Đồng ý", command=lambda: self.capture_qr_images(qr_data))
        btn.pack(pady=(0, 20), ipadx=10, ipady=5)

    def capture_qr_images(self, qr_data):
        if self.qr_capture_popup is not None:
            self.qr_capture_popup.destroy()
            self.qr_capture_popup = None
        os.makedirs('qr_captures', exist_ok=True)
        captured_paths = []
        name = qr_data.split('\n')[0].split(':')[-1].strip() if ':' in qr_data else qr_data.split('\n')[0].strip()
        name_safe = ''.join(c for c in name if c.isalnum() or c in ('-_'))
        for i in range(5):
            ret, frame = self.controller.read_webcam_frame()
            if ret:
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                img_path = f"qr_captures/{name_safe}_{ts}_{i+1}.jpg"
                cv2.imwrite(img_path, frame)
                captured_paths.append(img_path)
            self.update()
            time.sleep(1)
        # Sau khi lưu xong, gọi lại recognition_system để lưu QR lên Google Sheet
        if self.recognition_system is not None:
            self.recognition_system.save_qr_attendance(qr_data)
        else:
            self.write_log("recognition_system chưa được khởi tạo, không thể lưu QR.")
            messagebox.showerror("Lỗi", "Hệ thống nhận diện chưa sẵn sàng, không thể lưu QR lên Google Sheet.")
        self.qr_capture_in_progress = False
        # Hiện messagebox sau 5 giây
        self.after(5000, lambda: messagebox.showinfo("Hoàn tất", "Đã lưu ảnh thành công!")) 

    def _update_sysinfo(self):
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        self.sysinfo_label.config(text=f"CPU: {cpu}%  RAM: {ram}%")
        self.after(1500, self._update_sysinfo) 