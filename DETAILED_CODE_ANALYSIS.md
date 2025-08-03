# Phân Tích Chi Tiết Code Hệ Thống

## 🔧 Core Module - recognition_class.py

### **Class RecognitionSystem**

#### **1. Khởi Tạo (__init__)**
```python
def __init__(self, sheet_name="Attendance", credentials_path='credentials/face-attendance.json', pir_pin=17, gui_log_func=None, tts_enabled=True):
    # Khởi tạo logging
    self.setup_logging()
    
    # Cấu hình AI models
    self.FACE_RECOGNITION_THRESHOLD = 0.65  # Ngưỡng nhận diện khuôn mặt
    self.ANTISPOOF_THRESHOLD = 0.6         # Ngưỡng chống giả mạo
    self.MIN_FACE_SIZE = 50                 # Kích thước khuôn mặt tối thiểu
    
    # Khởi tạo các thành phần AI
    self.fasnet = self._initialize_fasnet()  # Model chống giả mạo
    self.mtcnn = MTCNN(keep_all=True, device='cpu')  # Phát hiện khuôn mặt
    self.train_data, self.label_encoder = self._load_training_data()  # Dữ liệu training
    
    # Kết nối Google Sheets
    self.sheet = self.setup_google_sheets(sheet_name, credentials_path)
    
    # Offline storage
    self.offline_syncer = OfflineAttendanceSync()
    
    # Trạng thái hệ thống
    self.google_sheets_offline = False  # Theo dõi trạng thái offline
    self.running = False
    self.cap = None
```

#### **2. Vòng Lặp Chính (run)**
```python
def run(self):
    """Vòng lặp chính xử lý frame từ camera"""
    self.running = True
    
    # Khởi tạo camera
    self.cap = cv2.VideoCapture(0)
    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    self.cap.set(cv2.CAP_PROP_FPS, 20)
    
    # Biến theo dõi thời gian
    last_check_time = time.time()
    last_sync_time = time.time()
    last_sheet_check_time = time.time()
    
    while self.running:
        # 1. Đồng bộ offline định kỳ (chỉ khi đã mất kết nối)
        current_time = time.time()
        if self.google_sheets_offline and current_time - last_sync_time > 300:
            self.sync_offline_data()
            last_sync_time = current_time
        
        # 2. Thử kết nối lại Google Sheets (mỗi 10 phút)
        if current_time - last_sheet_check_time > 600:
            if (not self.sheet or self.google_sheets_offline) and self.check_internet_connection():
                self.sheet = self.setup_google_sheets("Attendance", 'credentials/face-attendance.json')
            last_sheet_check_time = current_time
        
        # 3. Xử lý PIR sensor
        if self.pir_sensor and self.pir_sensor.is_motion():
            # Bật camera khi có chuyển động
            pass
        
        # 4. Đọc frame từ camera
        ret, frame = self.cap.read()
        if not ret:
            continue
        
        # 5. Nhận diện khuôn mặt
        faces, _ = self.detect_and_recognize(frame)
        
        # 6. Hiển thị kết quả
        for face in faces:
            # Vẽ khung và tên lên frame
            pass
        
        # 7. Gửi frame cho GUI
        try:
            self.frame_for_gui.put_nowait(cv2.resize(frame, (640, 480)))
        except queue.Full:
            pass
```

#### **3. Nhận Diện Khuôn Mặt (detect_and_recognize)**
```python
def detect_and_recognize(self, frame):
    """Phát hiện và nhận diện khuôn mặt trong frame"""
    all_faces_info = []
    
    # 1. Chuyển đổi màu sắc
    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # 2. Phát hiện khuôn mặt bằng MTCNN
    detect_result = self.mtcnn.detect(image_rgb)
    boxes, probs = detect_result[:2]
    
    # 3. Xử lý từng khuôn mặt
    for idx, box in enumerate(boxes):
        x1, y1, x2, y2 = [int(b) for b in box]
        w, h = x2 - x1, y2 - y1
        
        # Kiểm tra kích thước khuôn mặt
        if w < self.MIN_FACE_SIZE or h < self.MIN_FACE_SIZE:
            continue
        
        facial_area = {'x': x1, 'y': y1, 'w': w, 'h': h}
        
        # 4. Chống giả mạo (Anti-spoofing)
        is_real, antispoof_score = self.fasnet.analyze(frame, (x1, y1, w, h))
        if not is_real or antispoof_score < self.ANTISPOOF_THRESHOLD:
            all_faces_info.append({'name': 'Fake', 'facial_area': facial_area, 'confidence': antispoof_score})
            continue
        
        # 5. Nhận diện khuôn mặt thật
        face_img = self.preprocess_face(frame, (x1, y1, w, h))
        embedding = self.get_face_embedding(face_img)
        
        # 6. So sánh với dữ liệu training
        similarities = cosine_similarity([embedding], self.train_data['embeddings'])[0]
        best_match_index = np.argmax(similarities)
        confidence = similarities[best_match_index]
        
        if confidence >= self.FACE_RECOGNITION_THRESHOLD:
            predicted_label = self.train_data['labels'][best_match_index]
            name = self.label_encoder.inverse_transform([int(predicted_label)])[0]
            
            # 7. Kiểm tra trùng lặp và điểm danh
            is_duplicate = name in self.known_persons
            if not is_duplicate:
                self.known_persons.add(name)
                self.log_attendance(name, confidence, "FACE", is_duplicate=False)
            
            all_faces_info.append({'name': name, 'facial_area': facial_area, 'confidence': confidence})
        else:
            all_faces_info.append({'name': 'Unknown', 'facial_area': facial_area, 'confidence': confidence})
    
    return all_faces_info, []
```

#### **4. Ghi Điểm Danh (log_attendance)**
```python
def log_attendance(self, name, confidence, mode, is_duplicate=False):
    """Ghi điểm danh với timestamp chính xác"""
    # Tạo timestamp tại thời điểm điểm danh
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Định dạng confidence
    try:
        confidence_str = f"{float(confidence)*100:.1f} %"
    except Exception:
        confidence_str = str(confidence)
    
    record = (timestamp, name, mode, confidence_str)
    
    # Thử lưu lên Google Sheets
    if not is_duplicate and self.sheet:
        try:
            self.sheet.append_row(list(record))
            logging.info(f"Đã lưu lên Sheets: {name} ({mode})")
            self.google_sheets_offline = False  # Reset trạng thái offline
        except Exception as e:
            logging.error(f"Lỗi ghi Google Sheets: {e}")
            self.google_sheets_offline = True  # Set trạng thái offline
            # Lưu offline với timestamp chính xác
            self.offline_syncer.add_attendance(name, confidence, mode, timestamp)
            logging.info(f"Đã lưu điểm danh offline: {name} ({mode}) - {timestamp}")
    
    # Lưu offline khi không có kết nối Google Sheets
    elif not is_duplicate and not self.sheet:
        self.google_sheets_offline = True
        self.offline_syncer.add_attendance(name, confidence, mode, timestamp)
        logging.info(f"Đã lưu điểm danh offline: {name} ({mode}) - {timestamp}")
    
    # Phát âm thông báo
    if not is_duplicate and mode == "FACE" and self.tts_enabled:
        try:
            play_name_smart(f"Đã điểm danh thành công {name}")
        except Exception as e:
            logging.error(f"Lỗi TTS: {e}")
```

### **Class OfflineAttendanceSync**

#### **1. Khởi Tạo**
```python
def __init__(self, offline_file='offline_attendance.json'):
    # Tạo đường dẫn tuyệt đối cho file offline
    if not os.path.isabs(offline_file):
        offline_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), offline_file)
    
    self.offline_file = offline_file
    self.data = []
    self.load_offline_data()  # Load dữ liệu từ file
```

#### **2. Thêm Điểm Danh Offline**
```python
def add_attendance(self, name, confidence, data_type, timestamp):
    """Thêm điểm danh offline với kiểm tra trùng lặp"""
    # Kiểm tra trùng lặp trước khi thêm
    for existing_row in self.data:
        if (existing_row['timestamp'] == timestamp and 
            existing_row['data'] == str(name) and 
            existing_row['data_type'] == data_type):
            logging.info(f"Bỏ qua điểm danh trùng lặp: {name} ({data_type}) - {timestamp}")
            return
    
    # Tạo bản ghi mới
    row = {
        'timestamp': timestamp,
        'data': str(name),
        'data_type': data_type,
        'confidence': float(confidence)
    }
    
    self.data.append(row)
    self.save_offline_data()  # Lưu ngay lập tức
    logging.info(f"[OFFLINE] Đã lưu điểm danh offline: {row}")
```

#### **3. Đồng Bộ Lên Google Sheets**
```python
def sync_to_google_sheets(self, sheet):
    """Đồng bộ dữ liệu offline lên Google Sheets với kiểm tra trùng lặp"""
    if not self.data:
        logging.info("Không có dữ liệu offline cần đồng bộ.")
        return
    
    logging.info(f"Bắt đầu đồng bộ {len(self.data)} mục offline lên Google Sheets...")
    successful_syncs = 0
    failed_syncs = 0
    duplicate_syncs = 0
    
    # Lấy dữ liệu hiện tại từ Google Sheets để kiểm tra trùng lặp
    try:
        existing_data = sheet.get_all_values()
        existing_records = set()
        if len(existing_data) > 1:  # Có header + dữ liệu
            for row in existing_data[1:]:  # Bỏ qua header
                if len(row) >= 4:  # Đảm bảo có đủ 4 cột
                    # Tạo key để kiểm tra trùng lặp: timestamp + name + data_type
                    key = f"{row[0]}_{row[1]}_{row[2]}"
                    existing_records.add(key)
    except Exception as e:
        logging.warning(f"Không thể lấy dữ liệu hiện tại từ Google Sheets: {e}")
        existing_records = set()
    
    # Đồng bộ từng mục
    for i, row in enumerate(self.data[:]):  # Copy list để tránh lỗi khi modify
        # Tạo key để kiểm tra trùng lặp
        sync_key = f"{row['timestamp']}_{row['data']}_{row['data_type']}"
        
        # Kiểm tra trùng lặp
        if sync_key in existing_records:
            logging.info(f"Bỏ qua mục trùng lặp: {row['data']} ({row['data_type']}) - {row['timestamp']}")
            self.data.remove(row)  # Xóa khỏi danh sách offline
            duplicate_syncs += 1
            continue
        
        # Thử đồng bộ
        try:
            sheet.append_row([
                row['timestamp'], 
                row['data'], 
                row['data_type'], 
                f"{row.get('confidence', 0):.4f}"
            ])
            self.data.remove(row)  # Xóa khỏi danh sách sau khi đồng bộ thành công
            successful_syncs += 1
            logging.info(f"Đồng bộ thành công: {row['data']} ({row['data_type']}) - {row['timestamp']}")
        except Exception as e:
            failed_syncs += 1
            logging.error(f"Lỗi đồng bộ mục {i+1}: {e}")
            continue
    
    # Lưu lại danh sách còn lại
    if successful_syncs > 0 or duplicate_syncs > 0:
        self.save_offline_data()
        logging.info(f"Đồng bộ hoàn tất: {successful_syncs} thành công, {duplicate_syncs} trùng lặp, {failed_syncs} thất bại. Còn lại {len(self.data)} mục chưa đồng bộ.")
    else:
        logging.warning(f"Không có mục nào được đồng bộ thành công. Sẽ thử lại lần sau.")
```

### **Class Fasnet (Anti-Spoofing)**

#### **1. Khởi Tạo Model**
```python
def __init__(self):
    """Khởi tạo model chống giả mạo"""
    logging.info("Khởi tạo Fasnet...")
    
    # Kiểm tra PyTorch
    try:
        import torch
    except Exception as err:
        logging.error("Cần cài đặt torch: `pip install torch`")
        raise ValueError("Cần cài đặt torch") from err
    
    # Cấu hình device
    device = torch.device("cpu")
    self.device = device
    
    # Đường dẫn model
    home = os.path.expanduser("~")
    model_path = f"{home}/.deepface/weights/2.7_80x80_MiniFASNetV2.pth"
    model_url = "https://github.com/minivision-ai/Silent-Face-Anti-Spoofing/raw/master/resources/anti_spoof_models/2.7_80x80_MiniFASNetV2.pth"
    
    # Tải model nếu chưa có
    self.download_model(model_path, model_url)
    
    # Load model
    try:
        from deepface.models.spoofing import FasNetBackbone
        self.model = FasNetBackbone.MiniFASNetV2(conv6_kernel=(5, 5)).to(device)
        state_dict = torch.load(model_path, map_location=device)
        
        # Xử lý state dict
        if next(iter(state_dict)).find("module.") >= 0:
            from collections import OrderedDict
            new_state_dict = OrderedDict()
            for key, value in state_dict.items():
                name_key = key[7:]  # Bỏ "module."
                new_state_dict[name_key] = value
            self.model.load_state_dict(new_state_dict)
        else:
            self.model.load_state_dict(state_dict)
        
        self.model.eval()
    except Exception as e:
        logging.error(f"Lỗi khởi tạo mô hình MiniFASNetV2: {str(e)}")
        raise
```

#### **2. Phân Tích Khuôn Mặt**
```python
def analyze(self, img, facial_area: tuple):
    """Phân tích khuôn mặt thật/giả"""
    try:
        x, y, w, h = facial_area
        
        # Kiểm tra kích thước
        if w < 50 or h < 50:
            return False, 0.0
        
        # Crop khuôn mặt
        img_cropped = self.crop(img, (x, y, w, h), 2.7, 80, 80)
        
        # Chuyển đổi thành tensor
        test_transform = self.Compose([self.ToTensor(self)])
        img_tensor = test_transform(img_cropped)
        
        if isinstance(img_tensor, np.ndarray):
            img_tensor = torch.from_numpy(img_tensor)
        
        img_tensor = img_tensor.unsqueeze(0).to(self.device)
        
        # Dự đoán
        with torch.no_grad():
            result = self.model.forward(img_tensor)
            result = F.softmax(result, dim=1).cpu().numpy()
        
        # Kết quả
        label = np.argmax(result)
        is_real = label == 1  # 1 = thật, 0 = giả
        score = result[0][label]
        
        return is_real, score
        
    except Exception as e:
        logging.error(f"[ANTI-SPOOF] Lỗi phân tích: {e}", exc_info=True)
        return False, 0.0
```

## 🖥️ GUI Module - recognition_frame.py

### **Class RecognitionFrame**

#### **1. Khởi Tạo Giao Diện**
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

#### **2. Khởi Động Hệ Thống**
```python
def start_recognition_system(self):
    """Khởi động hệ thống nhận diện"""
    if self.running:
        self.write_log("Hệ thống đã đang chạy!")
        return
    
    self.write_log("Đang khởi động hệ thống nhận diện...")
    
    try:
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
        
        self.running = True
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        
        self.write_log("Hệ thống nhận diện đã khởi động thành công!")
        
    except Exception as e:
        self.write_log(f"Lỗi khởi động hệ thống: {e}")
        self.reset_state(log=False)
```

#### **3. Vòng Lặp Webcam**
```python
def _webcam_loop(self):
    """Vòng lặp xử lý webcam"""
    try:
        # Khởi động recognition system
        self.recognition_system.run()
    except Exception as e:
        self.write_log(f"Lỗi trong webcam loop: {e}")
    finally:
        self.running = False
```

#### **4. Vòng Lặp Nhận Diện**
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

#### **5. Dừng Hệ Thống**
```python
def stop_recognition_system_force(self):
    """Dừng hoàn toàn hệ thống nhận diện"""
    self.write_log("Dừng hoàn toàn hệ thống nhận diện...")
    self.force_stopped = True
    self.auto_mode = False
    
    # Dừng các thread
    self.running = False
    
    if hasattr(self, 'webcam_thread') and self.webcam_thread and self.webcam_thread.is_alive():
        self.webcam_thread.join(timeout=1)
    if hasattr(self, 'recognition_thread') and self.recognition_thread and self.recognition_thread.is_alive():
        self.recognition_thread.join(timeout=1)
    
    # Cập nhật giao diện
    self.start_btn.config(state='normal', text='Khởi động lại')
    self.stop_btn.config(state='disabled')
    self.webcam_status_var.set('Hệ thống đã dừng hoàn toàn.')
    
    self.write_log("Hệ thống đã dừng hoàn toàn. Không tự khởi động lại cho đến khi bấm 'Khởi động lại'.")
```

## 🌐 Web Application - app.py

### **Flask Routes**

#### **1. Trang Chủ**
```python
@app.route('/')
def index():
    """Trang chủ"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Lấy thống kê
    total_users = len(db.get_all_users())
    today_attendance = len(db.get_attendance_records(
        start_date=datetime.now().strftime('%Y-%m-%d')
    ))
    
    return render_template('index.html', 
                         total_users=total_users, 
                         today_attendance=today_attendance)
```

#### **2. Upload Ảnh**
```python
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Upload ảnh người dùng"""
    if request.method == 'POST':
        try:
            # Lấy thông tin từ form
            fullname = request.form['fullname']
            email = request.form.get('email', '')
            phone = request.form.get('phone', '')
            department = request.form.get('department', '')
            
            # Thêm người dùng vào database
            user_id = db.add_user(fullname, email, phone, department)
            
            # Xử lý ảnh upload
            uploaded_files = request.files.getlist('images')
            saved_paths = save_face_images(user_id, uploaded_files)
            
            return jsonify({
                'success': True,
                'message': f'Đã lưu {len(saved_paths)} ảnh cho {fullname}',
                'user_id': user_id
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    return render_template('upload.html')
```

#### **3. Xem Điểm Danh**
```python
@app.route('/attendance')
@login_required
def attendance():
    """Xem dữ liệu điểm danh"""
    try:
        # Lấy dữ liệu từ Google Sheets
        attendance_data = get_attendance_data()
        
        if attendance_data is not None:
            # Chuyển đổi thành JSON
            attendance_list = []
            for _, row in attendance_data.iterrows():
                attendance_list.append({
                    'timestamp': row.iloc[0],
                    'name': row.iloc[1],
                    'method': row.iloc[2],
                    'confidence': row.iloc[3]
                })
            
            return jsonify(attendance_list)
        else:
            return jsonify([])
            
    except Exception as e:
        return jsonify({'error': str(e)})
```

#### **4. Tạo QR Code**
```python
@app.route('/qr', methods=['GET', 'POST'])
@login_required
def qr_code():
    """Tạo QR code cho khách"""
    if request.method == 'POST':
        try:
            # Lấy thông tin khách
            guest_name = request.form['guest_name']
            recipient_email = request.form['email']
            visit_date = request.form['visit_date']
            
            # Tạo thông tin khách
            guest_info = {
                'name': guest_name,
                'email': recipient_email,
                'visit_date': visit_date,
                'qr_id': str(uuid.uuid4())
            }
            
            # Tạo QR code
            qr_data = json.dumps(guest_info)
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            # Tạo ảnh QR code
            qr_image = qr.make_image(fill_color="black", back_color="white")
            qr_image_bytes = io.BytesIO()
            qr_image.save(qr_image_bytes, format='PNG')
            qr_image_bytes.seek(0)
            
            # Gửi email
            send_qr_email(recipient_email, guest_name, qr_image_bytes.getvalue(), guest_info)
            
            return jsonify({
                'success': True,
                'message': f'Đã gửi QR code cho {guest_name}'
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    return render_template('qr.html')
```

## 💾 Database - db.py

### **Class DatabaseManager**

#### **1. Khởi Tạo Database**
```python
def __init__(self, db_path='database.db'):
    """Khởi tạo kết nối database"""
    self.db_path = db_path
    self.conn = sqlite3.connect(db_path, check_same_thread=False)
    self.conn.row_factory = sqlite3.Row  # Cho phép truy cập bằng tên cột
    self.create_tables()

def create_tables(self):
    """Tạo các bảng cần thiết"""
    cursor = self.conn.cursor()
    
    # Bảng users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            department TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Bảng face_profiles
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS face_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            image_path TEXT,
            embedding_data BLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Bảng attendance_records
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            timestamp TIMESTAMP,
            method TEXT,
            confidence REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    self.conn.commit()
```

#### **2. Thêm Người Dùng**
```python
def add_user(self, fullname, email=None, phone=None, department=None):
    """Thêm người dùng mới"""
    cursor = self.conn.cursor()
    
    cursor.execute('''
        INSERT INTO users (fullname, email, phone, department)
        VALUES (?, ?, ?, ?)
    ''', (fullname, email, phone, department))
    
    user_id = cursor.lastrowid
    self.conn.commit()
    
    logging.info(f"Đã thêm người dùng: {fullname} (ID: {user_id})")
    return user_id
```

#### **3. Thêm Face Profile**
```python
def add_face_profile(self, user_id, image_path, embedding_data):
    """Thêm profile khuôn mặt"""
    cursor = self.conn.cursor()
    
    cursor.execute('''
        INSERT INTO face_profiles (user_id, image_path, embedding_data)
        VALUES (?, ?, ?)
    ''', (user_id, image_path, embedding_data))
    
    profile_id = cursor.lastrowid
    self.conn.commit()
    
    logging.info(f"Đã thêm face profile: User ID {user_id}, Profile ID {profile_id}")
    return profile_id
```

#### **4. Thêm Bản Ghi Điểm Danh**
```python
def add_attendance_record(self, user_id, timestamp, method, confidence):
    """Thêm bản ghi điểm danh"""
    cursor = self.conn.cursor()
    
    cursor.execute('''
        INSERT INTO attendance_records (user_id, timestamp, method, confidence)
        VALUES (?, ?, ?, ?)
    ''', (user_id, timestamp, method, confidence))
    
    record_id = cursor.lastrowid
    self.conn.commit()
    
    logging.info(f"Đã thêm attendance record: User ID {user_id}, Method {method}")
    return record_id
```

#### **5. Lấy Dữ Liệu**
```python
def get_all_users(self):
    """Lấy danh sách tất cả người dùng"""
    cursor = self.conn.cursor()
    cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
    return cursor.fetchall()

def get_attendance_records(self, start_date=None, end_date=None):
    """Lấy bản ghi điểm danh"""
    cursor = self.conn.cursor()
    
    query = '''
        SELECT ar.*, u.fullname 
        FROM attendance_records ar
        JOIN users u ON ar.user_id = u.id
    '''
    params = []
    
    if start_date:
        query += ' WHERE ar.timestamp >= ?'
        params.append(start_date)
    
    if end_date:
        if start_date:
            query += ' AND ar.timestamp <= ?'
        else:
            query += ' WHERE ar.timestamp <= ?'
        params.append(end_date)
    
    query += ' ORDER BY ar.timestamp DESC'
    
    cursor.execute(query, params)
    return cursor.fetchall()
```

## 🎯 Training - finish_train.py

### **Training Model**

#### **1. Chuẩn Bị Dữ Liệu**
```python
def prepare_training_data():
    """Chuẩn bị dữ liệu training"""
    logging.info("Bắt đầu chuẩn bị dữ liệu training...")
    
    # Lấy danh sách ảnh từ thư mục
    image_dir = 'images_attendance'
    if not os.path.exists(image_dir):
        logging.error(f"Thư mục {image_dir} không tồn tại!")
        return None, None
    
    # Thu thập ảnh và nhãn
    images = []
    labels = []
    label_mapping = {}
    current_label = 0
    
    for person_dir in os.listdir(image_dir):
        person_path = os.path.join(image_dir, person_dir)
        if os.path.isdir(person_path):
            label_mapping[person_dir] = current_label
            
            # Lấy tất cả ảnh của người này
            for img_file in os.listdir(person_path):
                if img_file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    img_path = os.path.join(person_path, img_file)
                    try:
                        # Load và preprocess ảnh
                        img = cv2.imread(img_path)
                        if img is not None:
                            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                            img = cv2.resize(img, (160, 160))
                            images.append(img)
                            labels.append(current_label)
                    except Exception as e:
                        logging.warning(f"Không thể load ảnh {img_path}: {e}")
            
            current_label += 1
    
    if not images:
        logging.error("Không tìm thấy ảnh nào để training!")
        return None, None
    
    # Chuyển đổi thành numpy arrays
    X = np.array(images)
    y = np.array(labels)
    
    logging.info(f"Đã chuẩn bị {len(X)} ảnh cho {len(label_mapping)} người")
    return X, y, label_mapping
```

#### **2. Training Model**
```python
def train_model():
    """Training model nhận diện khuôn mặt"""
    logging.info("Bắt đầu training model...")
    
    # Chuẩn bị dữ liệu
    X, y, label_mapping = prepare_training_data()
    if X is None:
        return False
    
    try:
        # Khởi tạo model
        model = Sequential([
            Conv2D(32, (3, 3), activation='relu', input_shape=(160, 160, 3)),
            MaxPooling2D((2, 2)),
            Conv2D(64, (3, 3), activation='relu'),
            MaxPooling2D((2, 2)),
            Conv2D(64, (3, 3), activation='relu'),
            Flatten(),
            Dense(64, activation='relu'),
            Dense(len(label_mapping), activation='softmax')
        ])
        
        # Compile model
        model.compile(optimizer='adam',
                     loss='sparse_categorical_crossentropy',
                     metrics=['accuracy'])
        
        # Training
        history = model.fit(X, y, epochs=50, validation_split=0.2)
        
        # Lưu model
        model.save('models/train_FN.h5')
        
        # Lưu label mapping
        with open('models/label_mapping.json', 'w') as f:
            json.dump(label_mapping, f)
        
        logging.info("Training hoàn tất!")
        return True
        
    except Exception as e:
        logging.error(f"Lỗi training: {e}")
        return False
```

---

**Đây là phân tích chi tiết các file code quan trọng nhất trong hệ thống. Mỗi phần đều có giải thích từng dòng code và cách chúng hoạt động cùng nhau.** 🎯 