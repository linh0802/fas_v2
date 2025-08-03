# Phân Tích Chi Tiết Code - Phần 4: Database và Training

## 💾 Database Module - db.py

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
    
    # Bảng users - Lưu thông tin người dùng
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
    
    # Bảng face_profiles - Lưu thông tin khuôn mặt
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
    
    # Bảng attendance_records - Lưu bản ghi điểm danh
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

**Giải thích từng bảng:**

1. **users table**:
   - `id`: Primary key tự động tăng
   - `fullname`: Tên đầy đủ (bắt buộc)
   - `email`: Email (tùy chọn)
   - `phone`: Số điện thoại (tùy chọn)
   - `department`: Phòng ban (tùy chọn)
   - `created_at`: Thời gian tạo

2. **face_profiles table**:
   - `id`: Primary key tự động tăng
   - `user_id`: Foreign key đến users table
   - `image_path`: Đường dẫn ảnh khuôn mặt
   - `embedding_data`: Dữ liệu embedding (BLOB)
   - `created_at`: Thời gian tạo

3. **attendance_records table**:
   - `id`: Primary key tự động tăng
   - `user_id`: Foreign key đến users table
   - `timestamp`: Thời gian điểm danh
   - `method`: Phương thức điểm danh (FACE/QR)
   - `confidence`: Độ tin cậy (0-100)
   - `created_at`: Thời gian tạo

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

**Giải thích:**

1. **Tạo cursor**: Để thực hiện SQL commands
2. **INSERT statement**: Thêm dữ liệu vào bảng users
3. **Parameterized query**: Tránh SQL injection
4. **`cursor.lastrowid`**: Lấy ID của record vừa thêm
5. **Commit**: Lưu thay đổi vào database
6. **Log**: Ghi log để theo dõi
7. **Return user_id**: Trả về ID để sử dụng sau

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

**Giải thích:**

1. **Parameters**:
   - `user_id`: ID của người dùng
   - `image_path`: Đường dẫn ảnh
   - `embedding_data`: Dữ liệu embedding (có thể None)
2. **INSERT**: Thêm vào bảng face_profiles
3. **Return profile_id**: ID của profile vừa tạo

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

**Giải thích:**

1. **Parameters**:
   - `user_id`: ID người dùng (có thể None cho khách)
   - `timestamp`: Thời gian điểm danh
   - `method`: Phương thức (FACE/QR)
   - `confidence`: Độ tin cậy
2. **INSERT**: Thêm vào bảng attendance_records
3. **Return record_id**: ID của record vừa tạo

#### **5. Lấy Dữ Liệu Người Dùng**
```python
def get_all_users(self):
    """Lấy danh sách tất cả người dùng"""
    cursor = self.conn.cursor()
    cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
    return cursor.fetchall()

def get_user_by_id(self, user_id):
    """Lấy thông tin người dùng theo ID"""
    cursor = self.conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    return cursor.fetchone()

def get_user_by_email(self, email):
    """Lấy thông tin người dùng theo email"""
    cursor = self.conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    return cursor.fetchone()
```

**Giải thích:**

1. **`get_all_users()`**: Lấy tất cả users, sắp xếp theo thời gian tạo
2. **`get_user_by_id()`**: Lấy user theo ID (primary key)
3. **`get_user_by_email()`**: Lấy user theo email (unique field)
4. **`fetchall()`**: Lấy tất cả records
5. **`fetchone()`**: Lấy 1 record đầu tiên

#### **6. Lấy Dữ Liệu Điểm Danh**
```python
def get_attendance_records(self, start_date=None, end_date=None, user_id=None):
    """Lấy bản ghi điểm danh với filter"""
    cursor = self.conn.cursor()
    
    query = '''
        SELECT ar.*, u.fullname 
        FROM attendance_records ar
        LEFT JOIN users u ON ar.user_id = u.id
    '''
    params = []
    conditions = []
    
    # Filter theo ngày bắt đầu
    if start_date:
        conditions.append('ar.timestamp >= ?')
        params.append(start_date)
    
    # Filter theo ngày kết thúc
    if end_date:
        conditions.append('ar.timestamp <= ?')
        params.append(end_date)
    
    # Filter theo user_id
    if user_id:
        conditions.append('ar.user_id = ?')
        params.append(user_id)
    
    # Thêm WHERE clause nếu có điều kiện
    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)
    
    query += ' ORDER BY ar.timestamp DESC'
    
    cursor.execute(query, params)
    return cursor.fetchall()
```

**Giải thích từng bước:**

1. **Base query**: JOIN với bảng users để lấy tên
2. **Dynamic conditions**: Xây dựng WHERE clause động
3. **Date filters**: Filter theo khoảng thời gian
4. **User filter**: Filter theo người dùng cụ thể
5. **Parameterized query**: Tránh SQL injection
6. **ORDER BY**: Sắp xếp theo thời gian giảm dần

#### **7. Lấy Face Profiles**
```python
def get_face_profiles_by_user(self, user_id):
    """Lấy tất cả face profiles của một user"""
    cursor = self.conn.cursor()
    cursor.execute('''
        SELECT * FROM face_profiles 
        WHERE user_id = ? 
        ORDER BY created_at DESC
    ''', (user_id,))
    return cursor.fetchall()

def get_all_face_profiles(self):
    """Lấy tất cả face profiles"""
    cursor = self.conn.cursor()
    cursor.execute('''
        SELECT fp.*, u.fullname 
        FROM face_profiles fp
        JOIN users u ON fp.user_id = u.id
        ORDER BY fp.created_at DESC
    ''')
    return cursor.fetchall()
```

**Giải thích:**

1. **`get_face_profiles_by_user()`**: Lấy profiles của user cụ thể
2. **`get_all_face_profiles()`**: Lấy tất cả profiles với tên user
3. **JOIN**: Kết hợp với bảng users để lấy tên
4. **ORDER BY**: Sắp xếp theo thời gian tạo

#### **8. Thống Kê**
```python
def get_attendance_stats(self, start_date=None, end_date=None):
    """Lấy thống kê điểm danh"""
    cursor = self.conn.cursor()
    
    query = '''
        SELECT 
            COUNT(*) as total_records,
            COUNT(DISTINCT ar.user_id) as unique_users,
            COUNT(CASE WHEN ar.method = 'FACE' THEN 1 END) as face_attendance,
            COUNT(CASE WHEN ar.method = 'QR' THEN 1 END) as qr_attendance,
            AVG(ar.confidence) as avg_confidence
        FROM attendance_records ar
    '''
    params = []
    conditions = []
    
    if start_date:
        conditions.append('ar.timestamp >= ?')
        params.append(start_date)
    
    if end_date:
        conditions.append('ar.timestamp <= ?')
        params.append(end_date)
    
    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)
    
    cursor.execute(query, params)
    return cursor.fetchone()
```

**Giải thích:**

1. **Aggregate functions**: COUNT, AVG để tính thống kê
2. **COUNT(*)**: Tổng số bản ghi
3. **COUNT(DISTINCT)**: Số người dùng duy nhất
4. **COUNT(CASE WHEN)**: Đếm theo phương thức
5. **AVG(confidence)**: Độ tin cậy trung bình

#### **9. Xóa Dữ Liệu**
```python
def delete_user(self, user_id):
    """Xóa người dùng và tất cả dữ liệu liên quan"""
    cursor = self.conn.cursor()
    
    try:
        # Xóa face profiles trước (foreign key constraint)
        cursor.execute('DELETE FROM face_profiles WHERE user_id = ?', (user_id,))
        
        # Xóa attendance records
        cursor.execute('DELETE FROM attendance_records WHERE user_id = ?', (user_id,))
        
        # Xóa user
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        
        self.conn.commit()
        logging.info(f"Đã xóa user ID {user_id} và tất cả dữ liệu liên quan")
        return True
        
    except Exception as e:
        self.conn.rollback()
        logging.error(f"Lỗi xóa user {user_id}: {e}")
        return False

def delete_face_profile(self, profile_id):
    """Xóa face profile"""
    cursor = self.conn.cursor()
    
    cursor.execute('DELETE FROM face_profiles WHERE id = ?', (profile_id,))
    self.conn.commit()
    
    logging.info(f"Đã xóa face profile ID {profile_id}")
    return True
```

**Giải thích:**

1. **Cascade delete**: Xóa theo thứ tự để tránh foreign key constraint
2. **Transaction**: Sử dụng try-catch để rollback nếu lỗi
3. **Logging**: Ghi log để theo dõi
4. **Return status**: Trả về True/False để biết kết quả

## 🎯 Training Module - finish_train.py

### **Training Model Functions**

#### **1. Chuẩn Bị Dữ Liệu Training**
```python
def prepare_training_data():
    """Chuẩn bị dữ liệu training từ thư mục ảnh"""
    logging.info("Bắt đầu chuẩn bị dữ liệu training...")
    
    # Đường dẫn thư mục ảnh
    image_dir = 'images_attendance'
    if not os.path.exists(image_dir):
        logging.error(f"Thư mục {image_dir} không tồn tại!")
        return None, None, None
    
    # Thu thập ảnh và nhãn
    images = []
    labels = []
    label_mapping = {}
    current_label = 0
    
    # Duyệt qua từng thư mục con (tên người)
    for person_dir in os.listdir(image_dir):
        person_path = os.path.join(image_dir, person_dir)
        
        # Kiểm tra là thư mục
        if os.path.isdir(person_path):
            # Thêm vào mapping
            label_mapping[person_dir] = current_label
            
            # Lấy tất cả ảnh của người này
            for img_file in os.listdir(person_path):
                if img_file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    img_path = os.path.join(person_path, img_file)
                    
                    try:
                        # Load và preprocess ảnh
                        img = cv2.imread(img_path)
                        if img is not None:
                            # Chuyển đổi màu sắc
                            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                            # Resize về kích thước chuẩn
                            img = cv2.resize(img, (160, 160))
                            # Normalize pixel values
                            img = img.astype(np.float32) / 255.0
                            
                            images.append(img)
                            labels.append(current_label)
                        else:
                            logging.warning(f"Không thể load ảnh: {img_path}")
                    except Exception as e:
                        logging.warning(f"Lỗi xử lý ảnh {img_path}: {e}")
            
            current_label += 1
    
    if not images:
        logging.error("Không tìm thấy ảnh nào để training!")
        return None, None, None
    
    # Chuyển đổi thành numpy arrays
    X = np.array(images)
    y = np.array(labels)
    
    logging.info(f"Đã chuẩn bị {len(X)} ảnh cho {len(label_mapping)} người")
    return X, y, label_mapping
```

**Giải thích từng bước:**

1. **Kiểm tra thư mục**: Đảm bảo thư mục images_attendance tồn tại
2. **Duyệt cấu trúc**: Mỗi thư mục con = 1 người
3. **Label mapping**: Tạo mapping tên người → số label
4. **Load ảnh**: Sử dụng OpenCV để load
5. **Preprocessing**:
   - Chuyển BGR → RGB
   - Resize về 160x160
   - Normalize pixel values (0-1)
6. **Error handling**: Log lỗi nếu không load được ảnh
7. **Return data**: Trả về X, y, label_mapping

#### **2. Tạo Model Architecture**
```python
def create_model(num_classes):
    """Tạo model CNN cho face recognition"""
    model = Sequential([
        # Convolutional layers
        Conv2D(32, (3, 3), activation='relu', input_shape=(160, 160, 3)),
        MaxPooling2D((2, 2)),
        
        Conv2D(64, (3, 3), activation='relu'),
        MaxPooling2D((2, 2)),
        
        Conv2D(64, (3, 3), activation='relu'),
        MaxPooling2D((2, 2)),
        
        Conv2D(128, (3, 3), activation='relu'),
        MaxPooling2D((2, 2)),
        
        # Flatten layer
        Flatten(),
        
        # Dense layers
        Dense(128, activation='relu'),
        Dropout(0.5),  # Prevent overfitting
        
        Dense(64, activation='relu'),
        Dropout(0.3),
        
        # Output layer
        Dense(num_classes, activation='softmax')
    ])
    
    return model
```

**Giải thích từng layer:**

1. **Conv2D layers**: 
   - 32 filters 3x3 → 64 filters → 128 filters
   - Tăng số filters để học features phức tạp hơn
2. **MaxPooling2D**: Giảm kích thước feature maps
3. **Flatten**: Chuyển từ 2D sang 1D
4. **Dense layers**: 
   - 128 neurons → 64 neurons → num_classes
   - Dropout để tránh overfitting
5. **Softmax**: Output xác suất cho từng class

#### **3. Training Model**
```python
def train_model():
    """Training model nhận diện khuôn mặt"""
    logging.info("Bắt đầu training model...")
    
    # Chuẩn bị dữ liệu
    X, y, label_mapping = prepare_training_data()
    if X is None:
        return False
    
    try:
        # Tạo model
        num_classes = len(label_mapping)
        model = create_model(num_classes)
        
        # Compile model
        model.compile(
            optimizer='adam',
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        # Data augmentation
        datagen = ImageDataGenerator(
            rotation_range=20,
            width_shift_range=0.2,
            height_shift_range=0.2,
            horizontal_flip=True,
            fill_mode='nearest'
        )
        
        # Training
        history = model.fit(
            datagen.flow(X, y, batch_size=32),
            epochs=50,
            validation_split=0.2,
            callbacks=[
                EarlyStopping(patience=10, restore_best_weights=True),
                ReduceLROnPlateau(factor=0.5, patience=5)
            ]
        )
        
        # Lưu model
        model.save('models/train_FN.h5')
        
        # Lưu label mapping
        with open('models/label_mapping.json', 'w') as f:
            json.dump(label_mapping, f, indent=2)
        
        # Lưu training history
        with open('models/training_history.json', 'w') as f:
            json.dump(history.history, f, indent=2)
        
        logging.info("Training hoàn tất!")
        return True
        
    except Exception as e:
        logging.error(f"Lỗi training: {e}")
        return False
```

**Giải thích từng bước:**

1. **Chuẩn bị dữ liệu**: Gọi `prepare_training_data()`
2. **Tạo model**: Gọi `create_model()` với số classes
3. **Compile**: 
   - Optimizer: Adam
   - Loss: sparse_categorical_crossentropy
   - Metrics: accuracy
4. **Data augmentation**: Tăng cường dữ liệu để tránh overfitting
5. **Training**:
   - 50 epochs
   - 20% validation split
   - Callbacks: Early stopping, Reduce LR
6. **Lưu model**: Save model và metadata

#### **4. Evaluate Model**
```python
def evaluate_model():
    """Đánh giá model đã train"""
    try:
        # Load model
        model = load_model('models/train_FN.h5')
        
        # Load test data
        X_test, y_test, _ = prepare_training_data()
        if X_test is None:
            return False
        
        # Evaluate
        loss, accuracy = model.evaluate(X_test, y_test)
        
        logging.info(f"Test accuracy: {accuracy:.4f}")
        logging.info(f"Test loss: {loss:.4f}")
        
        return True
        
    except Exception as e:
        logging.error(f"Lỗi evaluate model: {e}")
        return False
```

**Giải thích:**

1. **Load model**: Tải model đã train
2. **Load test data**: Chuẩn bị dữ liệu test
3. **Evaluate**: Tính accuracy và loss
4. **Log results**: Ghi kết quả đánh giá

#### **5. Predict Function**
```python
def predict_face(model, face_image, label_mapping):
    """Dự đoán khuôn mặt"""
    try:
        # Preprocess ảnh
        face_image = cv2.resize(face_image, (160, 160))
        face_image = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
        face_image = face_image.astype(np.float32) / 255.0
        face_image = np.expand_dims(face_image, axis=0)
        
        # Predict
        predictions = model.predict(face_image)
        predicted_class = np.argmax(predictions[0])
        confidence = predictions[0][predicted_class]
        
        # Map class về tên
        reverse_mapping = {v: k for k, v in label_mapping.items()}
        predicted_name = reverse_mapping.get(predicted_class, 'Unknown')
        
        return predicted_name, confidence
        
    except Exception as e:
        logging.error(f"Lỗi predict: {e}")
        return 'Unknown', 0.0
```

**Giải thích:**

1. **Preprocess**: Chuẩn bị ảnh giống training
2. **Predict**: Chạy model để dự đoán
3. **Post-process**: 
   - Lấy class có xác suất cao nhất
   - Map về tên người
4. **Return**: Tên và độ tin cậy

### **Main Training Script**
```python
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Training
    if train_model():
        logging.info("Training thành công!")
        
        # Evaluate
        if evaluate_model():
            logging.info("Evaluate thành công!")
        else:
            logging.error("Evaluate thất bại!")
    else:
        logging.error("Training thất bại!")
```

**Giải thích:**

1. **Setup logging**: Cấu hình log format
2. **Train model**: Gọi hàm training
3. **Evaluate**: Đánh giá model nếu train thành công
4. **Log results**: Ghi kết quả cuối cùng

---

**Đây là phân tích chi tiết phần 4 - Database và Training. Phần này chứa toàn bộ logic quản lý dữ liệu và training model.** 🎯 