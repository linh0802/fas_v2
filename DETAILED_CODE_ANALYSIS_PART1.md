# Phân Tích Chi Tiết Code - Phần 1: Core Module

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

**Giải thích từng phần:**

- **`setup_logging()`**: Thiết lập hệ thống log để ghi lại các hoạt động
- **`FACE_RECOGNITION_THRESHOLD = 0.65`**: Ngưỡng 65% để xác định nhận diện thành công
- **`ANTISPOOF_THRESHOLD = 0.6`**: Ngưỡng 60% để xác định khuôn mặt thật
- **`MIN_FACE_SIZE = 50`**: Kích thước tối thiểu của khuôn mặt (pixel)
- **`self.fasnet`**: Model chống giả mạo (anti-spoofing)
- **`self.mtcnn`**: Model phát hiện khuôn mặt
- **`self.train_data`**: Dữ liệu training đã được load
- **`self.sheet`**: Kết nối Google Sheets
- **`self.offline_syncer`**: Quản lý dữ liệu offline
- **`self.google_sheets_offline`**: Biến theo dõi trạng thái offline

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

**Giải thích từng bước:**

1. **Khởi tạo camera**: Mở camera với độ phân giải 640x480, 20 FPS
2. **Đồng bộ offline**: Chỉ đồng bộ khi đã phát hiện mất kết nối Google Sheets
3. **Thử kết nối lại**: Mỗi 10 phút thử kết nối lại Google Sheets
4. **PIR sensor**: Tiết kiệm năng lượng bằng cách tắt camera khi không có chuyển động
5. **Đọc frame**: Lấy frame từ camera
6. **Nhận diện**: Gọi hàm `detect_and_recognize()` để xử lý
7. **Hiển thị**: Vẽ khung và tên lên frame
8. **Gửi GUI**: Gửi frame đã xử lý cho giao diện

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

**Giải thích từng bước:**

1. **Chuyển đổi màu**: BGR → RGB (OpenCV sử dụng BGR, MTCNN cần RGB)
2. **Phát hiện khuôn mặt**: Sử dụng MTCNN để tìm vị trí khuôn mặt
3. **Lọc kích thước**: Bỏ qua khuôn mặt quá nhỏ
4. **Chống giả mạo**: Sử dụng FasNet để kiểm tra khuôn mặt thật/giả
5. **Preprocess**: Chuẩn bị ảnh khuôn mặt cho nhận diện
6. **Tạo embedding**: Chuyển đổi ảnh thành vector số
7. **So sánh**: Tính độ tương đồng với dữ liệu training
8. **Nhận diện**: Nếu độ tương đồng > 65% thì nhận diện thành công
9. **Điểm danh**: Ghi điểm danh nếu chưa trùng lặp

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

**Giải thích logic:**

1. **Timestamp chính xác**: Tạo thời gian tại thời điểm điểm danh
2. **Định dạng confidence**: Chuyển đổi thành phần trăm
3. **Thử Google Sheets**: Nếu có kết nối thì lưu trực tiếp
4. **Lưu offline**: Nếu Google Sheets lỗi hoặc không có kết nối
5. **Cập nhật trạng thái**: Set `google_sheets_offline` để theo dõi
6. **TTS**: Phát âm thông báo nếu được bật

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

**Giải thích:**
- **Đường dẫn tuyệt đối**: Đảm bảo file được tạo đúng vị trí
- **`self.data`**: List chứa dữ liệu offline
- **`load_offline_data()`**: Load dữ liệu từ file JSON

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

**Giải thích:**
1. **Kiểm tra trùng lặp**: So sánh timestamp, name, data_type
2. **Tạo bản ghi**: Dictionary chứa thông tin điểm danh
3. **Thêm vào list**: Append vào `self.data`
4. **Lưu file**: Gọi `save_offline_data()` để lưu ngay

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

**Giải thích từng bước:**

1. **Kiểm tra dữ liệu**: Nếu không có dữ liệu offline thì return
2. **Lấy dữ liệu hiện tại**: Từ Google Sheets để kiểm tra trùng lặp
3. **Tạo key**: `timestamp_name_data_type` để so sánh
4. **Kiểm tra trùng lặp**: Nếu đã có trên Google Sheets thì bỏ qua
5. **Đồng bộ**: Thử ghi lên Google Sheets
6. **Xóa khỏi offline**: Sau khi đồng bộ thành công
7. **Thống kê**: Đếm số lượng thành công/thất bại/trùng lặp
8. **Lưu lại**: Cập nhật file offline với dữ liệu còn lại

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

**Giải thích:**

1. **Kiểm tra PyTorch**: Đảm bảo thư viện đã được cài đặt
2. **Cấu hình device**: Sử dụng CPU (có thể thay đổi thành GPU)
3. **Đường dẫn model**: Tải model từ GitHub nếu chưa có
4. **Load model**: Khởi tạo MiniFASNetV2
5. **Xử lý state dict**: Loại bỏ prefix "module." nếu có
6. **Set eval mode**: Chuyển model sang chế độ evaluation

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

**Giải thích từng bước:**

1. **Kiểm tra kích thước**: Bỏ qua khuôn mặt quá nhỏ
2. **Crop khuôn mặt**: Cắt khuôn mặt với tỷ lệ 2.7, resize về 80x80
3. **Chuyển đổi tensor**: Chuyển ảnh thành PyTorch tensor
4. **Dự đoán**: Chạy model để phân tích
5. **Softmax**: Chuyển đổi kết quả thành xác suất
6. **Kết quả**: Trả về (is_real, score)

---

**Đây là phân tích chi tiết phần 1 - Core Module. Phần này chứa toàn bộ logic nhận diện khuôn mặt và quản lý dữ liệu offline.** 🎯 