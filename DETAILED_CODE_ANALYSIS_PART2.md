# Phân Tích Chi Tiết Code - Phần 2: GUI Modules

## 🖥️ GUI Module - recognition_frame.py

### **Class RecognitionFrame**

#### **1. Khởi Tạo Giao Diện (__init__)**
```python
def __init__(self, parent, controller):
    super().__init__(parent, bg=DARK_BG)
    
    # Khởi tạo các biến
    self.controller = controller
    self.running = False
    self.recognition_system = None
    self.webcam_thread = None
    self.recognition_thread = None
    
    # Khởi tạo giao diện
    self._setup_ui()
    self._setup_variables()
    self._setup_touch_support()
```

**Giải thích từng phần:**
- **`self.controller`**: Tham chiếu đến controller chính của ứng dụng
- **`self.running`**: Biến boolean theo dõi trạng thái chạy của hệ thống
- **`self.recognition_system`**: Instance của RecognitionSystem
- **`self.webcam_thread`**: Thread xử lý webcam
- **`self.recognition_thread`**: Thread xử lý nhận diện
- **`_setup_ui()`**: Thiết lập giao diện người dùng
- **`_setup_variables()`**: Khởi tạo các biến cần thiết
- **`_setup_touch_support()`**: Hỗ trợ cảm ứng cho Raspberry Pi

#### **2. Thiết Lập Giao Diện (_setup_ui)**
```python
def _setup_ui(self):
    """Thiết lập giao diện người dùng"""
    # Frame chính
    main_frame = tk.Frame(self, bg=DARK_BG)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Tiêu đề
    title_label = tk.Label(main_frame, text="Hệ Thống Nhận Diện Khuôn Mặt", 
                          font=('Arial', 16, 'bold'), fg=WHITE, bg=DARK_BG)
    title_label.pack(pady=(0, 20))
    
    # Frame chứa video và controls
    content_frame = tk.Frame(main_frame, bg=DARK_BG)
    content_frame.pack(fill=tk.BOTH, expand=True)
    
    # Frame video (bên trái)
    self.video_frame = tk.Frame(content_frame, bg=BLACK, width=640, height=480)
    self.video_frame.pack(side=tk.LEFT, padx=(0, 20))
    self.video_frame.pack_propagate(False)  # Giữ kích thước cố định
    
    # Label hiển thị video
    self.video_label = tk.Label(self.video_frame, bg=BLACK)
    self.video_label.pack(expand=True, fill=tk.BOTH)
    
    # Frame controls (bên phải)
    controls_frame = tk.Frame(content_frame, bg=DARK_BG)
    controls_frame.pack(side=tk.RIGHT, fill=tk.Y)
    
    # Nút điều khiển
    self.start_btn = tk.Button(controls_frame, text="Khởi Động", 
                               command=self.start_recognition_system,
                               bg=GREEN, fg=WHITE, font=('Arial', 12, 'bold'),
                               width=15, height=2)
    self.start_btn.pack(pady=(0, 10))
    
    self.stop_btn = tk.Button(controls_frame, text="Dừng", 
                              command=self.stop_recognition_system,
                              bg=RED, fg=WHITE, font=('Arial', 12, 'bold'),
                              width=15, height=2, state='disabled')
    self.stop_btn.pack(pady=(0, 10))
    
    # Checkbox TTS
    self.tts_enabled = tk.BooleanVar(value=True)
    tts_checkbox = tk.Checkbutton(controls_frame, text="Bật TTS", 
                                  variable=self.tts_enabled,
                                  bg=DARK_BG, fg=WHITE, selectcolor=DARK_BG,
                                  font=('Arial', 10))
    tts_checkbox.pack(pady=(0, 10))
    
    # Trạng thái webcam
    self.webcam_status_var = tk.StringVar(value="Chưa khởi động")
    status_label = tk.Label(controls_frame, textvariable=self.webcam_status_var,
                           bg=DARK_BG, fg=WHITE, font=('Arial', 10))
    status_label.pack(pady=(0, 10))
    
    # Frame log
    log_frame = tk.Frame(controls_frame, bg=DARK_BG)
    log_frame.pack(fill=tk.BOTH, expand=True)
    
    # Text widget cho log
    self.log_text = tk.Text(log_frame, height=15, width=40, 
                           bg=BLACK, fg=GREEN, font=('Courier', 9))
    log_scrollbar = tk.Scrollbar(log_frame, orient=tk.VERTICAL, 
                                 command=self.log_text.yview)
    self.log_text.configure(yscrollcommand=log_scrollbar.set)
    
    self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
```

**Giải thích từng phần:**

1. **Main Frame**: Container chính chứa toàn bộ giao diện
2. **Title Label**: Tiêu đề ứng dụng
3. **Content Frame**: Chia thành 2 phần - video và controls
4. **Video Frame**: 
   - Kích thước cố định 640x480
   - `pack_propagate(False)`: Giữ kích thước không thay đổi
   - `video_label`: Hiển thị video stream
5. **Controls Frame**: Chứa các nút điều khiển và thông tin
6. **Start/Stop Buttons**: Điều khiển hệ thống
7. **TTS Checkbox**: Bật/tắt Text-to-Speech
8. **Status Label**: Hiển thị trạng thái webcam
9. **Log Text**: Hiển thị log hoạt động với scrollbar

#### **3. Thiết Lập Biến (_setup_variables)**
```python
def _setup_variables(self):
    """Thiết lập các biến cần thiết"""
    # Biến theo dõi trạng thái
    self.force_stopped = False
    self.auto_mode = True
    
    # Queue cho frame từ recognition system
    self.frame_for_gui = queue.Queue(maxsize=10)
    
    # Biến theo dõi thời gian
    self.last_face_detection = time.time()
    self.face_detection_timeout = 5.0  # 5 giây
    
    # Biến cho auto restart
    self.restart_count = 0
    self.max_restarts = 3
    self.restart_delay = 10  # 10 giây
```

**Giải thích từng biến:**

- **`self.force_stopped`**: Đánh dấu khi người dùng dừng thủ công
- **`self.auto_mode`**: Chế độ tự động khởi động lại
- **`self.frame_for_gui`**: Queue chứa frame từ recognition system
- **`self.last_face_detection`**: Thời điểm phát hiện khuôn mặt cuối cùng
- **`self.face_detection_timeout`**: Thời gian timeout cho việc phát hiện khuôn mặt
- **`self.restart_count`**: Số lần đã restart
- **`self.max_restarts`**: Số lần restart tối đa
- **`self.restart_delay`**: Thời gian chờ trước khi restart

#### **4. Khởi Động Hệ Thống (start_recognition_system)**
```python
def start_recognition_system(self):
    """Khởi động hệ thống nhận diện"""
    if self.running:
        self.write_log("Hệ thống đã đang chạy!")
        return
    
    self.write_log("Đang khởi động hệ thống nhận diện...")
    
    try:
        # Reset trạng thái
        self.force_stopped = False
        self.auto_mode = True
        
        # Khởi tạo recognition system
        self.recognition_system = RecognitionSystem(
            gui_log_func=self.write_log,
            tts_enabled=self.tts_enabled.get()
        )
        
        # Khởi động các thread
        self.webcam_thread = threading.Thread(target=self._webcam_loop, daemon=True)
        self.recognition_thread = threading.Thread(target=self._recognition_loop, daemon=True)
        
        self.webcam_thread.start()
        self.recognition_thread.start()
        
        # Cập nhật giao diện
        self.running = True
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.webcam_status_var.set('Hệ thống đang chạy')
        
        self.write_log("Hệ thống nhận diện đã khởi động thành công!")
        
    except Exception as e:
        self.write_log(f"Lỗi khởi động hệ thống: {e}")
        self.reset_state(log=False)
```

**Giải thích từng bước:**

1. **Kiểm tra trạng thái**: Nếu đã chạy thì return
2. **Reset biến**: Đặt lại các biến trạng thái
3. **Khởi tạo RecognitionSystem**: Tạo instance với callback log
4. **Tạo threads**: Thread cho webcam và recognition
5. **Start threads**: Khởi động các thread với `daemon=True`
6. **Cập nhật UI**: Thay đổi trạng thái nút và label
7. **Xử lý lỗi**: Nếu có lỗi thì reset state

#### **5. Vòng Lặp Webcam (_webcam_loop)**
```python
def _webcam_loop(self):
    """Vòng lặp xử lý webcam"""
    try:
        # Khởi động recognition system
        self.recognition_system.run()
    except Exception as e:
        self.write_log(f"Lỗi trong webcam loop: {e}")
    finally:
        # Đảm bảo dừng khi có lỗi
        self.running = False
        self.webcam_status_var.set('Hệ thống đã dừng')
        
        # Auto restart nếu cần
        if not self.force_stopped and self.auto_mode and self.restart_count < self.max_restarts:
            self.write_log(f"Tự động khởi động lại sau {self.restart_delay} giây... (Lần {self.restart_count + 1}/{self.max_restarts})")
            self.restart_count += 1
            
            # Schedule restart
            self.after(self.restart_delay * 1000, self._auto_restart)
        elif self.restart_count >= self.max_restarts:
            self.write_log("Đã đạt giới hạn số lần restart. Vui lòng khởi động lại thủ công.")
            self.auto_mode = False
```

**Giải thích logic:**

1. **Chạy recognition system**: Gọi `run()` method
2. **Xử lý lỗi**: Log lỗi nếu có
3. **Cleanup**: Đảm bảo dừng khi có lỗi
4. **Auto restart**: 
   - Kiểm tra điều kiện restart
   - Tăng counter restart
   - Schedule restart sau delay
5. **Giới hạn restart**: Dừng auto restart khi đạt giới hạn

#### **6. Vòng Lặp Nhận Diện (_recognition_loop)**
```python
def _recognition_loop(self):
    """Vòng lặp xử lý nhận diện"""
    while self.running:
        try:
            # Lấy frame từ recognition system
            if self.recognition_system and hasattr(self.recognition_system, 'frame_for_gui'):
                try:
                    frame = self.recognition_system.frame_for_gui.get(timeout=0.1)
                    self._update_video_feed(frame)
                except queue.Empty:
                    continue
        except Exception as e:
            self.write_log(f"Lỗi trong recognition loop: {e}")
            break
```

**Giải thích:**

1. **Vòng lặp chính**: Chạy khi `self.running = True`
2. **Lấy frame**: Từ queue `frame_for_gui` với timeout 0.1s
3. **Cập nhật video**: Gọi `_update_video_feed()` để hiển thị
4. **Xử lý timeout**: Nếu queue empty thì continue
5. **Xử lý lỗi**: Log lỗi và break loop

#### **7. Cập Nhật Video Feed (_update_video_feed)**
```python
def _update_video_feed(self, frame):
    """Cập nhật video feed trên GUI"""
    try:
        # Resize frame cho GUI
        frame_resized = cv2.resize(frame, (640, 480))
        
        # Chuyển đổi màu sắc
        frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
        
        # Chuyển đổi thành PhotoImage
        frame_pil = Image.fromarray(frame_rgb)
        frame_tk = ImageTk.PhotoImage(frame_pil)
        
        # Cập nhật label
        self.video_label.configure(image=frame_tk)
        self.video_label.image = frame_tk  # Giữ reference
        
        # Cập nhật trạng thái
        self.webcam_status_var.set('Camera đang hoạt động')
        
    except Exception as e:
        self.write_log(f"Lỗi cập nhật video feed: {e}")
```

**Giải thích từng bước:**

1. **Resize frame**: Đưa về kích thước 640x480 cho GUI
2. **Chuyển đổi màu**: BGR → RGB (OpenCV → PIL)
3. **Chuyển đổi format**: PIL Image → PhotoImage cho Tkinter
4. **Cập nhật label**: Gán image cho video_label
5. **Giữ reference**: Đảm bảo image không bị garbage collect
6. **Cập nhật status**: Thay đổi trạng thái webcam

#### **8. Dừng Hệ Thống (stop_recognition_system)**
```python
def stop_recognition_system(self):
    """Dừng hệ thống nhận diện"""
    self.write_log("Đang dừng hệ thống nhận diện...")
    
    # Đánh dấu dừng thủ công
    self.force_stopped = True
    self.auto_mode = False
    
    # Dừng recognition system
    if self.recognition_system:
        try:
            self.recognition_system.stop()
        except Exception as e:
            self.write_log(f"Lỗi khi dừng recognition system: {e}")
    
    # Dừng các thread
    self.running = False
    
    # Đợi threads kết thúc
    if hasattr(self, 'webcam_thread') and self.webcam_thread and self.webcam_thread.is_alive():
        self.webcam_thread.join(timeout=2)
    if hasattr(self, 'recognition_thread') and self.recognition_thread and self.recognition_thread.is_alive():
        self.recognition_thread.join(timeout=2)
    
    # Cập nhật giao diện
    self.start_btn.config(state='normal')
    self.stop_btn.config(state='disabled')
    self.webcam_status_var.set('Hệ thống đã dừng')
    
    # Reset restart counter
    self.restart_count = 0
    
    self.write_log("Hệ thống đã dừng thành công.")
```

**Giải thích từng bước:**

1. **Đánh dấu dừng**: Set `force_stopped = True` để ngăn auto restart
2. **Dừng recognition system**: Gọi `stop()` method
3. **Dừng threads**: Set `running = False` và join threads
4. **Cập nhật UI**: Thay đổi trạng thái nút và label
5. **Reset counter**: Đặt lại số lần restart
6. **Log kết quả**: Thông báo dừng thành công

#### **9. Auto Restart (_auto_restart)**
```python
def _auto_restart(self):
    """Tự động khởi động lại hệ thống"""
    if not self.force_stopped and self.auto_mode:
        self.write_log("Đang tự động khởi động lại hệ thống...")
        self.start_recognition_system()
```

**Giải thích:**

- **Kiểm tra điều kiện**: Chỉ restart nếu không bị force stop và đang ở auto mode
- **Khởi động lại**: Gọi `start_recognition_system()`

#### **10. Ghi Log (write_log)**
```python
def write_log(self, message):
    """Ghi log message vào text widget"""
    try:
        # Thêm timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        # Thêm vào text widget
        self.log_text.insert(tk.END, log_message)
        
        # Auto scroll xuống cuối
        self.log_text.see(tk.END)
        
        # Giới hạn số dòng log (tránh memory leak)
        lines = self.log_text.get("1.0", tk.END).split('\n')
        if len(lines) > 1000:  # Giữ tối đa 1000 dòng
            self.log_text.delete("1.0", "500.0")  # Xóa 500 dòng đầu
            
    except Exception as e:
        print(f"Lỗi ghi log: {e}")
```

**Giải thích:**

1. **Timestamp**: Thêm thời gian vào log message
2. **Insert**: Thêm message vào text widget
3. **Auto scroll**: Cuộn xuống dòng cuối cùng
4. **Memory management**: Giới hạn số dòng để tránh memory leak
5. **Error handling**: Xử lý lỗi khi ghi log

### **Class PIRSensor**

#### **1. Khởi Tạo**
```python
def __init__(self, pin=17):
    """Khởi tạo PIR sensor"""
    self.pin = pin
    self.last_motion_time = 0
    self.motion_timeout = 5.0  # 5 giây
    
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.IN)
        self.gpio_available = True
    except ImportError:
        self.gpio_available = False
        logging.warning("RPi.GPIO không có sẵn, PIR sensor sẽ không hoạt động")
```

**Giải thích:**

- **`self.pin`**: GPIO pin number cho PIR sensor
- **`self.last_motion_time`**: Thời điểm phát hiện chuyển động cuối cùng
- **`self.motion_timeout`**: Thời gian timeout cho motion detection
- **GPIO setup**: Thiết lập GPIO cho Raspberry Pi
- **Fallback**: Nếu không có RPi.GPIO thì disable PIR

#### **2. Kiểm Tra Chuyển Động**
```python
def is_motion(self):
    """Kiểm tra có chuyển động không"""
    if not self.gpio_available:
        return True  # Luôn trả về True nếu không có GPIO
    
    try:
        import RPi.GPIO as GPIO
        current_time = time.time()
        
        # Đọc trạng thái PIR sensor
        motion_detected = GPIO.input(self.pin) == GPIO.HIGH
        
        if motion_detected:
            self.last_motion_time = current_time
            return True
        else:
            # Kiểm tra timeout
            if current_time - self.last_motion_time < self.motion_timeout:
                return True
            return False
            
    except Exception as e:
        logging.error(f"Lỗi đọc PIR sensor: {e}")
        return True  # Trả về True để đảm bảo camera hoạt động
```

**Giải thích logic:**

1. **Kiểm tra GPIO**: Nếu không có GPIO thì luôn return True
2. **Đọc sensor**: Đọc trạng thái HIGH/LOW từ GPIO pin
3. **Cập nhật thời gian**: Nếu có motion thì update `last_motion_time`
4. **Timeout check**: Nếu chưa quá timeout thì vẫn coi như có motion
5. **Error handling**: Nếu có lỗi thì return True để đảm bảo camera hoạt động

### **Class SmartTTS**

#### **1. Khởi Tạo**
```python
def __init__(self):
    """Khởi tạo Text-to-Speech engine"""
    try:
        self.engine = pyttsx3.init()
        
        # Cấu hình voice
        voices = self.engine.getProperty('voices')
        if voices:
            # Tìm voice tiếng Việt hoặc voice đầu tiên
            for voice in voices:
                if 'vietnamese' in voice.name.lower() or 'vi' in voice.id.lower():
                    self.engine.setProperty('voice', voice.id)
                    break
            else:
                # Sử dụng voice đầu tiên nếu không tìm thấy tiếng Việt
                self.engine.setProperty('voice', voices[0].id)
        
        # Cấu hình tốc độ và âm lượng
        self.engine.setProperty('rate', 150)  # Tốc độ nói
        self.engine.setProperty('volume', 0.8)  # Âm lượng
        
        self.available = True
        
    except Exception as e:
        logging.error(f"Không thể khởi tạo TTS engine: {e}")
        self.available = False
```

**Giải thích:**

1. **Khởi tạo engine**: Sử dụng pyttsx3
2. **Tìm voice tiếng Việt**: Duyệt qua các voice có sẵn
3. **Fallback**: Nếu không có tiếng Việt thì dùng voice đầu tiên
4. **Cấu hình**: Tốc độ 150, âm lượng 80%
5. **Error handling**: Nếu lỗi thì disable TTS

#### **2. Phát Âm**
```python
def speak(self, text):
    """Phát âm text"""
    if not self.available:
        return
    
    try:
        # Dừng phát âm hiện tại nếu có
        self.engine.stop()
        
        # Phát âm text mới
        self.engine.say(text)
        self.engine.runAndWait()
        
    except Exception as e:
        logging.error(f"Lỗi phát âm: {e}")
```

**Giải thích:**

1. **Kiểm tra availability**: Nếu TTS không khả dụng thì return
2. **Stop current**: Dừng phát âm hiện tại
3. **Say text**: Đưa text vào queue
4. **Run and wait**: Phát âm và đợi hoàn thành
5. **Error handling**: Log lỗi nếu có

---

**Đây là phân tích chi tiết phần 2 - GUI Modules. Phần này chứa toàn bộ logic giao diện người dùng và các thành phần hỗ trợ.** 🎯 