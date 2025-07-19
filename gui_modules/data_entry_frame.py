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

    def switch_to_recognition(self):
        """Chuyển về frame nhận diện và giải phóng webcam"""
        self.stop_processes()
        # Đảm bảo webcam được giải phóng hoàn toàn
        self.controller.release_webcam()
        self.controller.show_frame('RecognitionFrame')

    def start_processes(self):
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
                self.controller.write_log(f"Đã nhận diện: {most_common_name} (trung bình {avg_conf:.2f})")
            else:
                self._auto_detect_running = False
                self.name_entry.config(state='normal')
                self.detected_name = None
                self.controller.write_log("Không nhận diện được ai, vui lòng nhập tên mới.")
            return
        ret, frame = self.controller.read_webcam_frame()
        if ret:
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = cv2.resize(img, (160, 160))
            name, conf = self.recog_simple.predict_name(img)
            self._auto_detect_names.append(name)
            self._auto_detect_confs.append(conf)
            self._auto_detect_frame_count += 1
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
        DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "database.db")
        if self.detected_name:  # User đã có
            name = self.detected_name
            valid_count = 0
            invalid_count = 0
            # Lấy user_id từ tên
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT user_id FROM users WHERE username=?", (name,))
            row = cur.fetchone()
            user_id = row[0] if row else None
            conn.close()
            for i, img_data in enumerate(self.pending_images):
                img = cv2.cvtColor(img_data, cv2.COLOR_BGR2RGB)
                img = cv2.resize(img, (160, 160))
                pred_name, conf = self.recog_simple.predict_name(img)
                if pred_name == name and conf > 0.65:
                    person_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'images_attendance', f"user_{user_id}")
                    os.makedirs(person_dir, exist_ok=True)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                    filename = os.path.join(person_dir, f"{timestamp}.jpg")
                    cv2.imwrite(filename, img_data)
                    # Cập nhật DB
                    if user_id:
                        conn = sqlite3.connect(DB_PATH)
                        cur = conn.cursor()
                        cur.execute("INSERT INTO face_profiles (user_id, image_path) VALUES (?, ?)", (user_id, filename))
                        conn.commit()
                        conn.close()
                    valid_count += 1
                else:
                    invalid_count += 1
            self.controller.write_log(f"Đã lưu {valid_count} ảnh hợp lệ, loại bỏ {invalid_count} ảnh không đúng.")
            messagebox.showinfo("Kết quả", f"Đã lưu {valid_count} ảnh hợp lệ, loại bỏ {invalid_count} ảnh không đúng.")
            self.clear_pending_images()
        else:  # User mới
            name = self.name_entry.get().strip()
            if not name:
                messagebox.showerror("Lỗi", "Tên không được để trống khi lưu.")
                return
            user_id = self.create_new_user_in_db(name)
            if user_id is None:
                messagebox.showerror("Lỗi", "Tên này đã tồn tại, vui lòng nhập tên khác!")
                return
            person_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'images_attendance', f"user_{user_id}")
            os.makedirs(person_dir, exist_ok=True)
            valid_count = 0
            duplicate_count = 0
            for i, img_data in enumerate(self.pending_images):
                img = cv2.cvtColor(img_data, cv2.COLOR_BGR2RGB)
                img = cv2.resize(img, (160, 160))
                pred_name, conf = self.recog_simple.predict_name(img)
                # Nếu predict ra tên khác Unknown và khác tên mới, tức là trùng người cũ
                if pred_name != "Unknown" and pred_name != name and conf > 0.65:
                    duplicate_count += 1
                    continue
                if pred_name == "Unknown" or conf < 0.65:
                    duplicate_count += 1
                    continue
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
            self.controller.write_log(f"Đã lưu {valid_count} ảnh mới, loại bỏ {duplicate_count} ảnh trùng với người cũ hoặc không phát hiện mặt.")
            messagebox.showinfo("Kết quả", f"Đã lưu {valid_count} ảnh mới, loại bỏ {duplicate_count} ảnh trùng với người cũ hoặc không phát hiện mặt.")
            self.clear_pending_images()

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

    def create_new_user_in_db(self, name):
        DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "database.db")
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        # Kiểm tra trùng tên
        cur.execute("SELECT COUNT(*) FROM users WHERE username = ?", (name,))
        if cur.fetchone()[0] > 0:
            conn.close()
            return None  # Tên đã tồn tại
        cur.execute("INSERT INTO users (username, full_name, password) VALUES (?, ?, ?)", (name, name, "1"))
        user_id = cur.lastrowid
        conn.commit()
        conn.close()
        return user_id

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
        self._auto_detect_running = True
        self._auto_detect_names = []  # Danh sách lưu kết quả tên predict
        self._auto_detect_confs = []  # Danh sách lưu xác suất
        self._auto_detect_frame_count = 0
        self.auto_detect_face_loop() 