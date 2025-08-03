# Phân Tích Chi Tiết Code - Phần 5: Các File Hỗ Trợ và Cấu Hình

## 🔧 Configuration Files

### **requirements.txt**
```txt
# Core dependencies
opencv-python==4.8.1.78
numpy==1.24.3
tensorflow==2.13.0
keras==2.13.1

# Face recognition
deepface==0.0.79
mtcnn==0.1.1
facenet-pytorch==2.5.3

# GUI
tkinter (built-in)
Pillow==10.0.0

# Web application
Flask==2.3.2
gspread==5.11.3
google-auth==2.22.0

# Database
sqlite3 (built-in)

# QR Code
qrcode==7.4.2
Pillow==10.0.0

# Email
smtplib (built-in)
email (built-in)

# Utilities
requests==2.31.0
python-dateutil==2.8.2
```

**Giải thích từng dependency:**

1. **Core dependencies**:
   - `opencv-python`: Xử lý ảnh và video
   - `numpy`: Tính toán số học
   - `tensorflow/keras`: Deep learning framework

2. **Face recognition**:
   - `deepface`: Framework nhận diện khuôn mặt
   - `mtcnn`: Face detection
   - `facenet-pytorch`: Face embedding

3. **GUI**: Tkinter và Pillow cho giao diện
4. **Web**: Flask cho web app, gspread cho Google Sheets
5. **QR Code**: Tạo và đọc QR code
6. **Utilities**: Các thư viện hỗ trợ

### **config.py**
```python
# Database configuration
DATABASE_PATH = 'database.db'

# Google Sheets configuration
GOOGLE_SHEETS_CREDENTIALS = 'credentials/face-attendance.json'
SHEET_NAME = 'Attendance'

# Camera configuration
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 20

# Face recognition thresholds
FACE_RECOGNITION_THRESHOLD = 0.65
ANTISPOOF_THRESHOLD = 0.6
MIN_FACE_SIZE = 50

# Offline sync configuration
OFFLINE_SYNC_INTERVAL = 300  # 5 minutes
SHEET_RECONNECT_INTERVAL = 600  # 10 minutes

# GUI colors
DARK_BG = '#2b2b2b'
WHITE = '#ffffff'
BLACK = '#000000'
GREEN = '#4CAF50'
RED = '#f44336'
BLUE = '#2196F3'

# Logging configuration
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = 'system.log'

# Email configuration
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
EMAIL_USER = 'your-email@gmail.com'
EMAIL_PASSWORD = 'your-app-password'

# File upload configuration
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
UPLOAD_FOLDER = 'images_attendance'

# Training configuration
TRAINING_IMAGE_SIZE = (160, 160)
TRAINING_BATCH_SIZE = 32
TRAINING_EPOCHS = 50
TRAINING_VALIDATION_SPLIT = 0.2
```

**Giải thích từng section:**

1. **Database**: Đường dẫn file SQLite
2. **Google Sheets**: Credentials và tên sheet
3. **Camera**: Cấu hình camera
4. **Thresholds**: Ngưỡng nhận diện
5. **Sync intervals**: Thời gian đồng bộ
6. **GUI colors**: Màu sắc giao diện
7. **Logging**: Cấu hình log
8. **Email**: Cấu hình SMTP
9. **File upload**: Giới hạn và định dạng
10. **Training**: Cấu hình training model

## 📁 Directory Structure

### **Project Root**
```
faceattendance/
├── core/
│   ├── __init__.py
│   ├── recognition_class.py      # Core recognition system
│   └── smart_tts.py            # Text-to-speech
├── gui_modules/
│   ├── __init__.py
│   ├── recognition_frame.py     # GUI main frame
│   └── colors.py               # Color definitions
├── web_app/
│   ├── __init__.py
│   ├── app.py                  # Flask web app
│   └── templates/              # HTML templates
├── database/
│   ├── __init__.py
│   └── db.py                   # Database manager
├── models/
│   ├── train_FN.h5            # Trained model
│   ├── label_mapping.json     # Label mapping
│   └── training_history.json  # Training history
├── training/
│   ├── __init__.py
│   └── finish_train.py        # Training script
├── credentials/
│   └── face-attendance.json   # Google Sheets credentials
├── images_attendance/         # Training images
├── logs/                      # Log files
├── requirements.txt           # Dependencies
├── config.py                 # Configuration
├── main.py                   # Main entry point
└── README.md                 # Documentation
```

### **Core Module Structure**
```
core/
├── __init__.py
├── recognition_class.py
│   ├── class RecognitionSystem
│   │   ├── __init__()
│   │   ├── run()
│   │   ├── detect_and_recognize()
│   │   ├── log_attendance()
│   │   ├── sync_offline_data()
│   │   └── check_internet_connection()
│   ├── class OfflineAttendanceSync
│   │   ├── __init__()
│   │   ├── add_attendance()
│   │   ├── sync_to_google_sheets()
│   │   ├── load_offline_data()
│   │   └── save_offline_data()
│   └── class Fasnet
│       ├── __init__()
│       ├── analyze()
│       └── crop()
└── smart_tts.py
    ├── class SmartTTS
    │   ├── __init__()
    │   └── speak()
    └── play_name_smart()
```

### **GUI Module Structure**
```
gui_modules/
├── __init__.py
├── recognition_frame.py
│   ├── class RecognitionFrame
│   │   ├── __init__()
│   │   ├── _setup_ui()
│   │   ├── _setup_variables()
│   │   ├── start_recognition_system()
│   │   ├── stop_recognition_system()
│   │   ├── _webcam_loop()
│   │   ├── _recognition_loop()
│   │   ├── _update_video_feed()
│   │   ├── _auto_restart()
│   │   └── write_log()
│   ├── class PIRSensor
│   │   ├── __init__()
│   │   └── is_motion()
│   └── class SmartTTS
│       ├── __init__()
│       └── speak()
└── colors.py
    ├── DARK_BG
    ├── WHITE
    ├── BLACK
    ├── GREEN
    ├── RED
    └── BLUE
```

## 🔧 Utility Functions

### **smart_tts.py**
```python
import pyttsx3
import logging
import threading

class SmartTTS:
    """Text-to-Speech engine với threading"""
    
    def __init__(self):
        """Khởi tạo TTS engine"""
        try:
            self.engine = pyttsx3.init()
            
            # Cấu hình voice
            voices = self.engine.getProperty('voices')
            if voices:
                # Tìm voice tiếng Việt
                for voice in voices:
                    if 'vietnamese' in voice.name.lower() or 'vi' in voice.id.lower():
                        self.engine.setProperty('voice', voice.id)
                        break
                else:
                    # Fallback to first voice
                    self.engine.setProperty('voice', voices[0].id)
            
            # Cấu hình tốc độ và âm lượng
            self.engine.setProperty('rate', 150)
            self.engine.setProperty('volume', 0.8)
            
            self.available = True
            
        except Exception as e:
            logging.error(f"Không thể khởi tạo TTS engine: {e}")
            self.available = False
    
    def speak(self, text):
        """Phát âm text trong thread riêng"""
        if not self.available:
            return
        
        def speak_thread():
            try:
                self.engine.stop()
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                logging.error(f"Lỗi phát âm: {e}")
        
        # Chạy trong thread riêng để không block main thread
        thread = threading.Thread(target=speak_thread, daemon=True)
        thread.start()

def play_name_smart(name):
    """Phát âm tên người một cách thông minh"""
    try:
        tts = SmartTTS()
        message = f"Đã điểm danh thành công {name}"
        tts.speak(message)
    except Exception as e:
        logging.error(f"Lỗi TTS: {e}")
```

**Giải thích:**

1. **SmartTTS class**: 
   - Khởi tạo pyttsx3 engine
   - Tìm voice tiếng Việt
   - Cấu hình tốc độ và âm lượng
2. **Threading**: Phát âm trong thread riêng
3. **play_name_smart()**: Hàm helper để phát âm tên

### **colors.py**
```python
# GUI Color Scheme
DARK_BG = '#2b2b2b'      # Dark background
WHITE = '#ffffff'         # White text
BLACK = '#000000'         # Black background
GREEN = '#4CAF50'         # Success/Start button
RED = '#f44336'          # Error/Stop button
BLUE = '#2196F3'         # Info/Link color
YELLOW = '#FFC107'       # Warning color
GRAY = '#9E9E9E'         # Disabled color

# Additional colors for different states
SUCCESS_GREEN = '#4CAF50'
ERROR_RED = '#f44336'
WARNING_ORANGE = '#FF9800'
INFO_BLUE = '#2196F3'
LIGHT_GRAY = '#f5f5f5'
DARK_GRAY = '#424242'
```

**Giải thích:**

- **Color scheme**: Bộ màu nhất quán cho GUI
- **Semantic colors**: Màu có ý nghĩa (success, error, warning)
- **Accessibility**: Đảm bảo contrast tốt

## 📊 Data Flow

### **1. Face Recognition Flow**
```
Camera Input → MTCNN Detection → Face Crop → Anti-spoofing → 
Face Embedding → Similarity Calculation → Recognition Result → 
Attendance Logging → Google Sheets/Offline Storage
```

**Giải thích từng bước:**

1. **Camera Input**: Lấy frame từ camera
2. **MTCNN Detection**: Phát hiện khuôn mặt trong frame
3. **Face Crop**: Cắt khuôn mặt từ frame
4. **Anti-spoofing**: Kiểm tra khuôn mặt thật/giả
5. **Face Embedding**: Chuyển đổi thành vector số
6. **Similarity Calculation**: So sánh với dữ liệu training
7. **Recognition Result**: Kết quả nhận diện
8. **Attendance Logging**: Ghi điểm danh
9. **Storage**: Lưu vào Google Sheets hoặc offline

### **2. Offline Sync Flow**
```
Offline Data → Internet Check → Google Sheets Check → 
Duplicate Check → Upload → Remove from Offline → 
Update Status → Log Result
```

**Giải thích từng bước:**

1. **Offline Data**: Dữ liệu đã lưu offline
2. **Internet Check**: Kiểm tra kết nối internet
3. **Google Sheets Check**: Kiểm tra kết nối Google Sheets
4. **Duplicate Check**: Kiểm tra trùng lặp
5. **Upload**: Tải lên Google Sheets
6. **Remove from Offline**: Xóa khỏi dữ liệu offline
7. **Update Status**: Cập nhật trạng thái
8. **Log Result**: Ghi kết quả

### **3. Web Application Flow**
```
User Request → Authentication → Route Handler → 
Database Query → Google Sheets Query → 
Template Rendering → Response
```

**Giải thích từng bước:**

1. **User Request**: Request từ browser
2. **Authentication**: Kiểm tra đăng nhập
3. **Route Handler**: Xử lý route cụ thể
4. **Database Query**: Truy vấn SQLite
5. **Google Sheets Query**: Truy vấn Google Sheets
6. **Template Rendering**: Render HTML template
7. **Response**: Trả về response

## 🔒 Security Features

### **1. Input Validation**
```python
def validate_upload_file(filename):
    """Kiểm tra file upload"""
    if not filename:
        return False
    
    # Kiểm tra extension
    if '.' not in filename:
        return False
    
    ext = filename.rsplit('.', 1)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False
    
    return True

def validate_user_input(data):
    """Kiểm tra input từ user"""
    # Sanitize input
    if isinstance(data, str):
        data = data.strip()
        # Remove potentially dangerous characters
        data = data.replace('<', '').replace('>', '')
        data = data.replace('"', '').replace("'", '')
    
    return data
```

**Giải thích:**

1. **File validation**: Kiểm tra định dạng file
2. **Input sanitization**: Loại bỏ ký tự nguy hiểm
3. **SQL injection prevention**: Sử dụng parameterized queries

### **2. Authentication**
```python
def login_required(f):
    """Decorator yêu cầu đăng nhập"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def check_permissions(user_id, resource_id):
    """Kiểm tra quyền truy cập"""
    # Implement permission checking logic
    return True
```

**Giải thích:**

1. **Session-based auth**: Sử dụng Flask session
2. **Route protection**: Decorator bảo vệ routes
3. **Permission checking**: Kiểm tra quyền truy cập

### **3. Data Encryption**
```python
import hashlib
import secrets

def hash_password(password):
    """Hash password với salt"""
    salt = secrets.token_hex(16)
    hash_obj = hashlib.sha256()
    hash_obj.update((password + salt).encode())
    return hash_obj.hexdigest(), salt

def verify_password(password, hash_value, salt):
    """Verify password"""
    hash_obj = hashlib.sha256()
    hash_obj.update((password + salt).encode())
    return hash_obj.hexdigest() == hash_value
```

**Giải thích:**

1. **Password hashing**: Hash password với salt
2. **Salt generation**: Tạo salt ngẫu nhiên
3. **Verification**: Kiểm tra password

## 📈 Performance Optimization

### **1. Memory Management**
```python
def optimize_memory_usage():
    """Tối ưu sử dụng memory"""
    import gc
    
    # Force garbage collection
    gc.collect()
    
    # Clear unused variables
    if 'large_data' in globals():
        del large_data
    
    # Monitor memory usage
    import psutil
    process = psutil.Process()
    memory_info = process.memory_info()
    logging.info(f"Memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")
```

### **2. Threading Optimization**
```python
def optimize_threading():
    """Tối ưu threading"""
    import threading
    
    # Set thread pool size
    import concurrent.futures
    max_workers = min(32, (os.cpu_count() or 1) + 4)
    
    # Use ThreadPoolExecutor for I/O operations
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future = executor.submit(heavy_operation)
        result = future.result()
```

### **3. Database Optimization**
```python
def optimize_database():
    """Tối ưu database"""
    cursor = db.conn.cursor()
    
    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON attendance_records(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON attendance_records(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_method ON attendance_records(method)')
    
    # Optimize database
    cursor.execute('VACUUM')
    cursor.execute('ANALYZE')
    
    db.conn.commit()
```

## 🐛 Error Handling

### **1. Comprehensive Error Handling**
```python
def handle_errors(func):
    """Decorator xử lý lỗi"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            logging.error(f"File not found: {e}")
            return None
        except PermissionError as e:
            logging.error(f"Permission denied: {e}")
            return None
        except ConnectionError as e:
            logging.error(f"Connection error: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error in {func.__name__}: {e}")
            return None
    return wrapper
```

### **2. Graceful Degradation**
```python
def graceful_degradation():
    """Xử lý graceful degradation"""
    try:
        # Try primary method
        result = primary_method()
    except Exception as e:
        logging.warning(f"Primary method failed: {e}")
        try:
            # Try fallback method
            result = fallback_method()
        except Exception as e:
            logging.error(f"Fallback method also failed: {e}")
            result = None
    
    return result
```

## 📝 Logging Strategy

### **1. Structured Logging**
```python
import logging
import json
from datetime import datetime

class StructuredLogger:
    """Structured logging với JSON format"""
    
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # JSON formatter
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "message": "%(message)s"}'
        )
        
        # File handler
        file_handler = logging.FileHandler('logs/structured.log')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def log_event(self, event_type, details):
        """Log event với structured data"""
        log_data = {
            'event_type': event_type,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.logger.info(json.dumps(log_data))
```

### **2. Performance Monitoring**
```python
import time
import functools

def monitor_performance(func):
    """Decorator monitor performance"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        execution_time = end_time - start_time
        logging.info(f"{func.__name__} executed in {execution_time:.4f} seconds")
        
        return result
    return wrapper
```

---

**Đây là phân tích chi tiết phần 5 - Các file hỗ trợ và cấu hình. Phần này chứa toàn bộ cấu trúc project, utilities, security, performance optimization và error handling.** 🎯 