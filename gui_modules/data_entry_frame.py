import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from PIL import Image, ImageTk
import cv2
import threading
import subprocess
import time
import os
import queue
from datetime import datetime
import sqlite3
import psutil

from .gui_config import *
from .gui_components import EnlargedFaceWindow, OnScreenKeyboardFrame
import sys
import os
# Thêm thư mục cha vào path để import các module khác
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.recognition_simple import RecognitionSimple
from config import get_database_path
class DataEntryFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=DARK_BG)
        self.controller = controller
        self._setup_variables()
        self._setup_ui()
        self._setup_touch_support()

        # Tạo label nhỏ ở góc phải dưới
        self.sysinfo_label = tk.Label(self, text="", font=("Arial", 9), fg="#888", bg=DARK_BG)
        self.sysinfo_label.place(relx=1.0, rely=1.0, anchor="se", x=-8, y=-8)  # Cách mép phải/dưới 8px

        def update_sysinfo():
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            self.sysinfo_label.config(text=f"CPU: {cpu}%  RAM: {ram}%")
            self.after(1500, update_sysinfo)  # Cập nhật mỗi 1.5 giây

        update_sysinfo()

    def _setup_variables(self):
        self.running_webcam = False
        self.webcam_thread = None
        self.current_frame = None
        self.cropped_preview_frame = None
        self.captured_image_thumbs = []
        self.pending_images = [] # Lưu ảnh tạm thời
        self.frame_queue = queue.Queue(maxsize=2)
        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(self, orient='horizontal', length=320, mode='determinate', variable=self.progress_var, maximum=100)
        self.progress_label = tk.Label(self, text='Tiến trình: 0%', font=('Arial', 12), fg=DARK_ACCENT, bg=DARK_BG)
        # Ban đầu ẩn
        self.progress_bar.pack_forget()
        self.progress_label.pack_forget()

        self.recog_simple = RecognitionSimple(model_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "train_FN.h5"))
        self.detected_name = None
        self.detected_confidence = 0
        
        # Khởi tạo các biến auto-detect
        self._auto_detect_running = False
        self._auto_detect_names = []
        self._auto_detect_confs = []
        self._auto_detect_frame_count = 0

    def _setup_ui(self):
        # --- Layout chính 2 cột ---
        main_frame = tk.Frame(self, bg=DARK_BG)
        main_frame.pack(side='top', fill='both', expand=True, padx=0, pady=0)
        
        # --- Cột Trái: Webcam Preview ---
        left_col = tk.Frame(main_frame, bg=DARK_BG)
        left_col.pack(side='left', fill='y', padx=0)

        webcam_container = tk.LabelFrame(
            left_col, 
            text="Webcam (Tỉ lệ 3:4)", 
            font=('Arial', 14, 'bold'), 
            bg=DARK_PANEL, 
            fg=DARK_ACCENT, 
            relief='groove', 
            bd=2, 
            labelanchor='n', 
            width=270, 
            height=360
        )
        webcam_container.pack(side='top', anchor='nw', padx=0, pady=0)
        self.video_label = tk.Label(webcam_container, bg='#11151c', width=270, height=360)
        self.video_label.pack(side='top', anchor='nw', padx=0, pady=0)

        # --- Cột Phải: Ảnh đã chụp ---
        right_col = tk.Frame(main_frame, bg=DARK_BG)
        right_col.pack(side='left', fill='both', expand=True, padx=0, pady=0)

        # Giảm chiều cao khung ảnh đã chụp
        captured_container = tk.LabelFrame(right_col, text="Ảnh đã chụp", font=('Arial', 14, 'bold'), bg=DARK_PANEL, fg=DARK_ACCENT, relief='groove', bd=2, labelanchor='n', height=387)
        captured_container.pack(side='top', fill='x', expand=False, pady=(0, 5))
        captured_container.pack_propagate(False)
        self.captured_container = captured_container
        self.captured_canvas = tk.Canvas(captured_container, bg=DARK_PANEL, highlightthickness=0, height=360)
        self.captured_canvas.pack(side='left', fill='both', expand=True)
        self.scrollable_frame = tk.Frame(self.captured_canvas, bg=DARK_PANEL)
        self.captured_canvas.create_window((30,0), window=self.scrollable_frame, anchor='nw')
        self.scrollable_frame.bind("<Configure>", lambda e: self.captured_canvas.configure(scrollregion=self.captured_canvas.bbox("all")))
        # Bàn phím ảo Frame (ẩn mặc định)
        self.keyboard_frame = None

        # --- Controls (nằm dưới main_frame, full width) ---
        controls_frame = tk.Frame(self, bg=DARK_BG)
        controls_frame.pack(side='top', fill='x')
        entry_frame = tk.Frame(controls_frame, bg=DARK_BG)
        entry_frame.pack(pady=2)
        self.entry_frame = entry_frame
        tk.Label(entry_frame, text="Nhập tên:", font=('Arial', 14), fg=DARK_TEXT, bg=DARK_BG).pack(side='left', padx=5)
        self.name_entry = tk.Entry(entry_frame, font=('Arial', 14), width=25)
        self.name_entry.pack(side='left')
        self.name_entry.bind("<Button-1>", self.show_keyboard_frame)
        self.name_entry.bind("<KeyRelease>", self.check_user_status)

        self.btn_frame = tk.Frame(controls_frame, bg=DARK_BG)
        self.btn_frame.pack(pady=5)
        # Thêm nút Nhận diện tự động
        self.auto_detect_btn = ttk.Button(self.btn_frame, text='Nhận diện tự động', command=self.start_auto_detect)
        self.auto_detect_btn.pack(side='left', padx=5)
        self.capture_btn = ttk.Button(self.btn_frame, text='Chụp 10 ảnh', command=self.capture_face)
        self.capture_btn.pack(side='left', padx=5)
        self.save_btn = ttk.Button(self.btn_frame, text='Lưu ảnh', command=self.save_captured_images)
        self.clear_btn = ttk.Button(self.btn_frame, text='Hủy bỏ', command=self.clear_pending_images)
        self.train_btn = ttk.Button(self.btn_frame, text='Huấn luyện', command=self.start_training)
        self.train_btn.pack(side='left', padx=5)
        self.back_btn = ttk.Button(self.btn_frame, text='Quay lại nhận diện', command=self.switch_to_recognition)
        self.back_btn.pack(side='left', padx=5)

        # --- Log (nằm dưới cùng, full width) ---
        log_frame = tk.Frame(self, height=100, bg=DARK_BG)
        log_frame.pack(side='bottom', fill='x', pady=(5,0))
        log_frame.pack_propagate(False)
        self.log_text = scrolledtext.ScrolledText(log_frame, font=('Consolas', 12), height=4, state='disabled', bg='#23272f', fg=DARK_TEXT)
        self.log_text.pack(side='bottom', fill='both', expand=True)

    def _setup_touch_support(self):
        # Thêm hỗ trợ vuốt cảm ứng cho log_text
        self.log_text.bind('<Button-1>', self._log_on_click)
        self.log_text.bind('<B1-Motion>', self._log_on_drag)
        self.log_text.bind('<ButtonRelease-1>', self._log_on_release)
        self._log_scroll_start_y = 0
        self._log_scroll_start_view = 0

    def write_log(self, msg):
        self.controller.write_log(msg)

    def switch_to_recognition(self):
        """Chuyển về màn hình nhận diện và dừng webcam"""
        if self.running_webcam:
            self.write_log("Hệ thống đang chuyển về nhận diện...")
            self.stop_webcam()
        self.controller.show_frame('RecognitionFrame')

    def start_processes(self):
        # Dừng hoàn toàn hệ thống nhận diện nếu đang chạy
        recognition_frame = self.controller.frames.get('RecognitionFrame')
        if recognition_frame and hasattr(recognition_frame, 'running') and recognition_frame.running:
            self.write_log("[CHUYỂN] Dừng hoàn toàn hệ thống nhận diện khi chuyển sang thêm dữ liệu...")
            if hasattr(recognition_frame, 'stop_recognition_system_force'):
                recognition_frame.stop_recognition_system_force()
        
        # Khởi tạo PIR monitoring cho cửa sổ này
        self.write_log("[PIR] Bắt đầu giám sát PIR ở cửa sổ thêm dữ liệu (timeout: 2 phút)")
        
        self.clear_pending_images() # Reset trạng thái khi frame được hiển thị
        self.name_entry.config(state='normal')  # Đảm bảo Entry luôn ở trạng thái nhập được
        self.name_entry.delete(0, 'end')        # Xóa nội dung cũ
        self.detected_name = None
        self.detected_confidence = 0
        self.start_webcam()
        # KHÔNG tự động gọi auto_detect_face_loop() nữa
        self._auto_detect_running = False # Đảm bảo biến này được reset
        self._auto_detect_names = []  # Danh sách lưu kết quả tên predict
        self._auto_detect_confs = []  # Danh sách lưu xác suất
        self._auto_detect_frame_count = 0
        # Reset trạng thái nút auto_detect
        self.auto_detect_btn.config(state='normal', text='Nhận diện tự động')

    def auto_detect_face_loop(self):
        # Nhận diện 10 frame đầu tiên khi vào giao diện, lấy tên xuất hiện nhiều nhất
        if not getattr(self, '_auto_detect_running', False):
            return
        if self._auto_detect_frame_count >= 10:
            # Đếm tần suất tên, loại Unknown và conf <= 0.65
            valid_names = [n for n, c in zip(self._auto_detect_names, self._auto_detect_confs) if n != "Unknown" and c > 0.65]
            if valid_names:
                from collections import Counter
                most_common_name, count = Counter(valid_names).most_common(1)[0]
                self.name_entry.delete(0, 'end')
                self.name_entry.insert(0, most_common_name)
                self.name_entry.config(state='disabled')
                self.detected_name = most_common_name
                # Lấy xác suất trung bình của tên này
                avg_conf = sum([c for n, c in zip(self._auto_detect_names, self._auto_detect_confs) if n == most_common_name]) / count
                self.detected_confidence = avg_conf
                self._auto_detect_running = False
                self.auto_detect_btn.config(state='normal', text='Nhận diện tự động')
                self.controller.write_log(f"Đã nhận diện: {most_common_name} (trung bình {avg_conf:.2f})")
            else:
                # Kiểm tra xem có phải người đã có trong database nhưng chưa có ảnh không
                DB_PATH = get_database_path()
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute("SELECT username FROM users")
                existing_users = [row[0] for row in cur.fetchall()]
                conn.close()
                
                # Đếm số frame có khuôn mặt
                face_frames = sum(1 for conf in self._auto_detect_confs if conf > 0.3)  # Ngưỡng thấp hơn để phát hiện khuôn mặt
                
                if face_frames >= 5:  # Có ít nhất 5 frame có khuôn mặt
                    self.controller.write_log("Phát hiện khuôn mặt nhưng chưa nhận diện được. Có thể là người mới hoặc người chưa có ảnh trong hệ thống.")
                    self.name_entry.config(state='normal')
                    self.detected_name = None
                else:
                    self.controller.write_log("Không phát hiện khuôn mặt rõ ràng, vui lòng điều chỉnh vị trí.")
                    self.name_entry.config(state='normal')
                    self.detected_name = None
                self._auto_detect_running = False
                self.auto_detect_btn.config(state='normal', text='Nhận diện tự động')
            return
        ret, frame = self.controller.read_webcam_frame()
        if ret:
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = cv2.resize(img, (160, 160))
            name, conf = self.recog_simple.predict_name(img)
            self._auto_detect_names.append(name)
            self._auto_detect_confs.append(conf)
            self._auto_detect_frame_count += 1
            
            # Hiển thị tiến trình
            progress = (self._auto_detect_frame_count / 10) * 100
            self.auto_detect_btn.config(text=f'Đang nhận diện... {progress:.0f}%')
            
        self.after(200, self.auto_detect_face_loop)

    def stop_processes(self):
        self.stop_webcam()
        # Đảm bảo webcam được giải phóng hoàn toàn
        self.controller.release_webcam()

    def start_webcam(self):
        if self.running_webcam: return
        
        # Sử dụng webcam chung từ controller
        if not self.controller.initialize_webcam():
            self.controller.write_log("Không thể khởi tạo webcam.")
            return
            
        self.running_webcam = True
        self.webcam_thread = threading.Thread(target=self.update_webcam_preview, daemon=True)
        self.webcam_thread.start()
        self.update_gui_from_queue()
        self.controller.write_log("Đã bật webcam preview.")

    def stop_webcam(self):
        if not self.running_webcam: return
        self.running_webcam = False 
        if self.webcam_thread and self.webcam_thread.is_alive():
            self.webcam_thread.join(timeout=1)
        # Không giải phóng webcam chung, chỉ dừng thread
        self.controller.write_log("Đã tắt webcam preview.")
        time.sleep(0.5)

    def update_gui_from_queue(self):
        try:
            display_frame = self.frame_queue.get_nowait()
            img = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(img)
            imgtk = ImageTk.PhotoImage(image=img_pil)
            self._imgtk_ref = imgtk  # Giữ tham chiếu để không bị thu gom rác
            self.video_label.config(image=imgtk)
        except queue.Empty:
            pass

        if self.running_webcam:
            self.after(30, self.update_gui_from_queue)

    def update_webcam_preview(self):
        while self.running_webcam:
            ret, frame = self.controller.read_webcam_frame()
            if not ret: 
                time.sleep(0.1)
                continue
            
            self.current_frame = frame.copy() 
            h, w, _ = frame.shape
            
            # Lấy chiều cao tối đa, chiều rộng = 3/4 chiều cao, crop chính giữa
            target_h = h
            target_w = int(target_h * 3 / 4)
            if target_w > w:
                target_w = w
                target_h = int(w * 4 / 3)
            start_x = (w - target_w) // 2
            start_y = (h - target_h) // 2
            cropped_frame = frame[start_y:start_y+target_h, start_x:start_x+target_w]
            self.cropped_preview_frame = cropped_frame.copy()
            display_frame = cv2.resize(cropped_frame, (270, 360))
            try:
                self.frame_queue.put_nowait(display_frame)
            except queue.Full: pass

    def capture_face(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Lỗi", "Vui lòng nhập tên người cần thêm.")
            return
        self.hide_keyboard_frame()  # Tắt bàn phím ảo khi bấm chụp
        self.capture_btn.config(state='disabled', text='Đang chụp...')
        self.clear_pending_images(clear_ui=False) # Xóa ảnh cũ nhưng không reset UI
        threading.Thread(target=self._capture_10_photos, args=(name,), daemon=True).start()

    def _capture_10_photos(self, name):
        self.controller.write_log(f"Bắt đầu chụp 10 ảnh cho '{name}'...")
        
        count = 0
        while count < 10:
            if not self.running_webcam or self.cropped_preview_frame is None:
                self.controller.write_log("Mất kết nối webcam hoặc không có ảnh, dừng chụp.")
                break
            
            # Lưu ảnh vào danh sách chờ
            self.pending_images.append(self.cropped_preview_frame.copy())
            self.controller.write_log(f"Đã chụp ảnh [{count + 1}/10]")
            self.after(0, self.add_captured_thumb, self.cropped_preview_frame.copy())
            
            count += 1
            time.sleep(0.2) 
        
        if self.pending_images:
            self.controller.write_log(f"Hoàn tất chụp ảnh. Vui lòng lưu hoặc hủy.")
            # Cập nhật UI sau khi chụp xong
            self.after(0, self.show_save_clear_buttons)
        else:
            # Nếu có lỗi, reset lại nút chụp
            self.after(0, lambda: self.capture_btn.config(state='normal', text='Chụp 10 ảnh'))

    def show_save_clear_buttons(self):
        self.capture_btn.pack_forget()
        self.save_btn.pack(side='left', padx=10)
        self.clear_btn.pack(side='left', padx=10)

    def hide_save_clear_buttons(self):
        self.save_btn.pack_forget()
        self.clear_btn.pack_forget()
        self.capture_btn.config(state='normal', text='Chụp 10 ảnh')
        self.capture_btn.pack(side='left', padx=10)

    def save_captured_images(self):
        DB_PATH = get_database_path()
        
        # Kiểm tra xem người đã có trong database chưa
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Lỗi", "Tên không được để trống khi lưu.")
            return
            
        # Kiểm tra trong database
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        # Kiểm tra user không phân biệt chữ hoa/thường
        cur.execute("SELECT user_id, username FROM users WHERE LOWER(username) = ?", (name.lower(),))
        row = cur.fetchone()
        conn.close()
        
        if not row:
            # User không tồn tại trong hệ thống
            messagebox.showerror("Lỗi", f"Người dùng '{name}' chưa có trong hệ thống. Vui lòng nhập tên người dùng đã có sẵn hoặc tạo user mới trước.")
            self.controller.write_log(f"Không thể lưu ảnh: User '{name}' chưa có trong hệ thống.")
            return
            
        user_id, actual_username = row
        
        valid_count = 0
        invalid_count = 0
        person_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'images_attendance', f"user_{user_id}")
        os.makedirs(person_dir, exist_ok=True)
        
        # Kiểm tra xem user đã có ảnh chưa
        has_existing_images = self.check_user_has_images(user_id)
        
        for i, img_data in enumerate(self.pending_images):
            img = cv2.cvtColor(img_data, cv2.COLOR_BGR2RGB)
            img = cv2.resize(img, (160, 160))
            pred_name, conf = self.recog_simple.predict_name(img)
            
            if has_existing_images:
                # HƯỚNG 1: User đã có ảnh trong hệ thống
                # Chỉ lưu ảnh nhận diện đúng tên, sai tên thì bỏ
                if pred_name == actual_username and conf > 0.65:
                    # Nhận diện đúng người
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                    filename = os.path.join(person_dir, f"{timestamp}.jpg")
                    cv2.imwrite(filename, img_data)
                    # Cập nhật DB
                    conn = sqlite3.connect(DB_PATH)
                    cur = conn.cursor()
                    cur.execute("INSERT INTO face_profiles (user_id, image_path) VALUES (?, ?)", (user_id, filename))
                    conn.commit()
                    conn.close()
                    valid_count += 1
                else:
                    # Nhận diện sai người hoặc không có khuôn mặt
                    invalid_count += 1
            else:
                # HƯỚNG 2: User chưa có ảnh trong hệ thống
                # Lưu các ảnh có khuôn mặt và nhận diện không thành công (Unknown)
                gray = cv2.cvtColor(img_data, cv2.COLOR_BGR2GRAY)
                faces = self.recog_simple.face_cascade.detectMultiScale(gray, 1.1, 4)
                
                if len(faces) > 0 and pred_name == "Unknown":
                    # Có khuôn mặt và nhận diện không thành công (Unknown)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                    filename = os.path.join(person_dir, f"{timestamp}.jpg")
                    cv2.imwrite(filename, img_data)
                    # Cập nhật DB
                    conn = sqlite3.connect(DB_PATH)
                    cur = conn.cursor()
                    cur.execute("INSERT INTO face_profiles (user_id, image_path) VALUES (?, ?)", (user_id, filename))
                    conn.commit()
                    conn.close()
                    valid_count += 1
                else:
                    # Không có khuôn mặt hoặc nhận diện được người khác
                    invalid_count += 1
                
        if not has_existing_images:
            self.controller.write_log(f"Đã lưu {valid_count} ảnh đầu tiên cho người dùng '{actual_username}', loại bỏ {invalid_count} ảnh không đúng.")
            messagebox.showinfo("Kết quả", f"Đã lưu {valid_count} ảnh đầu tiên cho người dùng '{actual_username}', loại bỏ {invalid_count} ảnh không đúng.")
        else:
            self.controller.write_log(f"Đã lưu {valid_count} ảnh hợp lệ, loại bỏ {invalid_count} ảnh không đúng.")
            messagebox.showinfo("Kết quả", f"Đã lưu {valid_count} ảnh hợp lệ, loại bỏ {invalid_count} ảnh không đúng.")
        
        # Sau khi lưu xong, kiểm tra tính toàn vẹn dữ liệu
        if valid_count > 0:
            self.verify_saved_images(user_id)
        
        self.clear_pending_images()

    def verify_saved_images(self, user_id):
        """Kiểm tra và sửa chữa tính toàn vẹn dữ liệu sau khi lưu"""
        DB_PATH = get_database_path()
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # Lấy tất cả ảnh của user từ DB
        cur.execute("SELECT profile_id, image_path FROM face_profiles WHERE user_id = ?", (user_id,))
        db_images = cur.fetchall()
        
        # Kiểm tra ảnh nào không tồn tại
        deleted_count = 0
        for profile_id, image_path in db_images:
            if not os.path.exists(image_path):
                cur.execute("DELETE FROM face_profiles WHERE profile_id = ?", (profile_id,))
                deleted_count += 1
                self.controller.write_log(f"Đã xóa record ảnh không tồn tại: {image_path}")
        
        if deleted_count > 0:
            conn.commit()
            self.controller.write_log(f"Đã dọn dẹp {deleted_count} record ảnh không tồn tại")
        
        conn.close()

    def clear_pending_images(self, clear_ui=True):
        self.pending_images.clear()
        self.captured_image_thumbs.clear()
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        if clear_ui:
            self.hide_save_clear_buttons()

    def add_captured_thumb(self, frame):
        thumb_w, thumb_h = 126, 168  # 3:4
        img_resized = cv2.resize(frame, (thumb_w, thumb_h))
        img = Image.fromarray(cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB))
        imgtk = ImageTk.PhotoImage(image=img)
        self.captured_image_thumbs.append(imgtk)
        thumb_label = tk.Label(self.scrollable_frame, image=imgtk, bg=DARK_PANEL)
        num_images = len(self.captured_image_thumbs) - 1
        # 1 hàng 5 ảnh, tự động xuống hàng
        col = num_images % 5
        row = num_images // 5
        # Padding trên/dưới lớn hơn padding trái/phải
        thumb_label.grid(row=row, column=col, padx=(4,4), pady=(4,4))
        # Thêm sự kiện click để phóng to ảnh
        def show_preview(event, img=frame):
            EnlargedFaceWindow(self, 'Preview', img)
        thumb_label.bind('<Button-1>', show_preview)

    def sync_database_before_training(self):
        """Đồng bộ database với folder trước khi train"""
        try:
            # Import function đồng bộ từ training module
            from training.check_training_data import sync_images_from_folders
            
            self.controller.write_log("Đang đồng bộ database với folder ảnh...")
            sync_results = sync_images_from_folders()
            
            if sync_results:
                self.controller.write_log(f"Đã đồng bộ DB: {sync_results['total_images_found']} ảnh")
                if sync_results['deleted_from_db'] > 0 or sync_results['added_to_db'] > 0:
                    self.controller.write_log(f"   - Xóa: {sync_results['deleted_from_db']}, Thêm: {sync_results['added_to_db']}")
            else:
                self.controller.write_log("Không thể đồng bộ database")
                
        except Exception as e:
            self.controller.write_log(f"Lỗi khi đồng bộ database: {e}")

    def start_training(self):
        if self.pending_images:
            if not messagebox.askyesno("Xác nhận", "Bạn có ảnh chưa được lưu. Nếu tiếp tục huấn luyện, các ảnh này sẽ bị mất. Bạn có muốn tiếp tục không?"):
                return
        self.clear_pending_images()
        self.stop_webcam()
        self.controller.release_webcam()
        self.controller.write_log("Đã tắt webcam và giải phóng tài nguyên trước khi huấn luyện.")
        self.capture_btn.config(state='disabled')
        self.save_btn.config(state='disabled')
        self.clear_btn.config(state='disabled')
        self.train_btn.config(state='disabled', text='Đang huấn luyện...')
        
        # Đồng bộ DB với folder trước khi train
        self.sync_database_before_training()
        
        self.controller.write_log("Bắt đầu quá trình huấn luyện lại (chế độ: thông minh)...")
        threading.Thread(target=self._run_train_script_with_mode, args=("--smart",), daemon=True).start()

    def _run_train_script_with_mode(self, mode):
        try:
            process = subprocess.Popen(
                ['python3', TRAIN_SCRIPT, mode],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            if process.stdout:
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        self.log_text.config(state='normal')
                        self.log_text.insert('end', output.strip() + '\n')
                        self.log_text.see('end')
                        self.log_text.config(state='disabled')
            rc = process.poll()
            if rc == 0:
                self.controller.write_log("Huấn luyện thành công!")
                messagebox.showinfo("Hoàn tất", "Quá trình huấn luyện lại đã hoàn tất thành công.")
                self.capture_btn.config(state='normal')
                self.save_btn.config(state='normal')
                self.clear_btn.config(state='normal')
                self.train_btn.config(state='normal', text='Huấn luyện lại')
            else:
                self.controller.write_log(f"Huấn luyện thất bại với mã lỗi: {rc}")
                messagebox.showerror("Lỗi", f"Quá trình huấn luyện gặp lỗi. Vui lòng kiểm tra log.")
        except Exception as e:
            self.controller.write_log(f"Lỗi nghiêm trọng khi chạy script: {e}")
            messagebox.showerror("Lỗi", f"Không thể bắt đầu quá trình huấn luyện: {e}")
        finally:
            self.train_btn.config(state='normal', text='Huấn luyện lại')

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

    def check_user_has_images(self, user_id):
        """Kiểm tra xem user đã có ảnh trong thư mục chưa"""
        person_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'images_attendance', f"user_{user_id}")
        if not os.path.exists(person_dir):
            return False
        image_files = [f for f in os.listdir(person_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        return len(image_files) > 0

    def check_user_status(self, event=None):
        """Kiểm tra và hiển thị trạng thái của user khi nhập tên"""
        name = self.name_entry.get().strip()
        if not name:
            return
            
        DB_PATH = get_database_path()
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # Kiểm tra user không phân biệt chữ hoa/thường
        cur.execute("SELECT user_id, username FROM users WHERE LOWER(username) = ?", (name.lower(),))
        row = cur.fetchone()
        conn.close()
        
        if row:
            user_id, actual_username = row
            has_images = self.check_user_has_images(user_id)
            if has_images:
                self.controller.write_log(f"Người dùng '{actual_username}' đã có trong hệ thống và có ảnh.")
            else:
                self.controller.write_log(f"Người dùng '{actual_username}' đã có trong hệ thống nhưng chưa có ảnh. Có thể thêm ảnh.")
        else:
            self.controller.write_log(f"Người dùng '{name}' chưa có trong hệ thống.")

    def show_keyboard_frame(self, event=None):
        if self.keyboard_frame is None or not self.keyboard_frame.winfo_ismapped():
            self.keyboard_frame = OnScreenKeyboardFrame(self.captured_container, self.name_entry)
            # Lấy chiều rộng khung ảnh đã chụp
            self.captured_container.update_idletasks()
            width = self.captured_container.winfo_width()
            height = self.keyboard_frame.winfo_reqheight()
            container_width = self.captured_container.winfo_width()
            keyboard_width = int(container_width * 0.9)  # 80% chiều rộng
            x_offset = (container_width - keyboard_width) // 2
            self.keyboard_frame.place(x=x_offset, y=self.captured_container.winfo_height()-height-25, width=keyboard_width)
        else:
            self.keyboard_frame.lift()
    
    def hide_keyboard_frame(self):
        if self.keyboard_frame and self.keyboard_frame.winfo_ismapped():
            self.keyboard_frame.place_forget() 

    def start_auto_detect(self):
        """Bắt đầu nhận diện tự động 10 frame đầu tiên"""
        if self._auto_detect_running:
            self.controller.write_log("Nhận diện tự động đang chạy...")
            return
            
        self.controller.write_log("Bắt đầu nhận diện tự động...")
        self.auto_detect_btn.config(state='disabled', text='Đang nhận diện...')
        self._auto_detect_running = True
        self._auto_detect_names = []  # Danh sách lưu kết quả tên predict
        self._auto_detect_confs = []  # Danh sách lưu xác suất
        self._auto_detect_frame_count = 0
        self.auto_detect_face_loop() 