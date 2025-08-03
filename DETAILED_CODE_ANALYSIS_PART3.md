# Phân Tích Chi Tiết Code - Phần 3: Web Application

## 🌐 Web Application - app.py

### **Flask App Configuration**

#### **1. Khởi Tạo Flask App**
```python
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Cần thiết cho session

# Cấu hình upload
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'images_attendance'

# Đảm bảo thư mục upload tồn tại
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
```

**Giải thích từng phần:**
- **`app.secret_key`**: Cần thiết để sử dụng Flask session
- **`MAX_CONTENT_LENGTH`**: Giới hạn kích thước file upload (16MB)
- **`UPLOAD_FOLDER`**: Thư mục lưu ảnh upload
- **`os.makedirs()`**: Tạo thư mục nếu chưa tồn tại

#### **2. Database Initialization**
```python
# Khởi tạo database
db = DatabaseManager()

# Khởi tạo Google Sheets connection
def get_google_sheets_data():
    """Lấy dữ liệu từ Google Sheets"""
    try:
        gc = gspread.service_account(filename='credentials/face-attendance.json')
        sheet = gc.open("Attendance").sheet1
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        logging.error(f"Lỗi kết nối Google Sheets: {e}")
        return None
```

**Giải thích:**
- **`DatabaseManager()`**: Khởi tạo kết nối SQLite
- **`get_google_sheets_data()`**: Hàm helper để lấy dữ liệu từ Google Sheets
- **Error handling**: Log lỗi nếu không kết nối được

### **Authentication Decorators**

#### **1. Login Required Decorator**
```python
def login_required(f):
    """Decorator để yêu cầu đăng nhập"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
```

**Giải thích:**
- **`@wraps(f)`**: Giữ nguyên metadata của function gốc
- **Kiểm tra session**: Nếu không có `user_id` trong session thì redirect về login
- **Return function**: Nếu đã đăng nhập thì chạy function gốc

### **Route Definitions**

#### **1. Trang Chủ (/)**
```python
@app.route('/')
def index():
    """Trang chủ"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Lấy thống kê từ database
        total_users = len(db.get_all_users())
        
        # Lấy thống kê điểm danh hôm nay
        today = datetime.now().strftime('%Y-%m-%d')
        today_attendance = len(db.get_attendance_records(start_date=today))
        
        # Lấy dữ liệu từ Google Sheets
        sheets_data = get_google_sheets_data()
        if sheets_data is not None:
            sheets_today = len(sheets_data[sheets_data.iloc[:, 0].str.contains(today, na=False)])
        else:
            sheets_today = 0
        
        return render_template('index.html', 
                             total_users=total_users, 
                             today_attendance=today_attendance,
                             sheets_today=sheets_today)
                             
    except Exception as e:
        logging.error(f"Lỗi trang chủ: {e}")
        return render_template('index.html', 
                             total_users=0, 
                             today_attendance=0,
                             sheets_today=0)
```

**Giải thích từng bước:**

1. **Kiểm tra đăng nhập**: Redirect nếu chưa đăng nhập
2. **Lấy thống kê database**: 
   - Tổng số người dùng
   - Số điểm danh hôm nay từ database
3. **Lấy thống kê Google Sheets**: 
   - Số điểm danh hôm nay từ Google Sheets
4. **Render template**: Truyền dữ liệu vào template
5. **Error handling**: Nếu có lỗi thì trả về giá trị mặc định

#### **2. Trang Đăng Nhập (/login)**
```python
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Trang đăng nhập"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Kiểm tra thông tin đăng nhập (đơn giản)
        if username == 'admin' and password == 'admin123':
            session['user_id'] = 1
            session['username'] = username
            return redirect(url_for('index'))
        else:
            flash('Thông tin đăng nhập không đúng!', 'error')
            return render_template('login.html')
    
    return render_template('login.html')
```

**Giải thích:**

1. **GET request**: Hiển thị form đăng nhập
2. **POST request**: Xử lý thông tin đăng nhập
3. **Kiểm tra credentials**: So sánh với username/password cố định
4. **Session management**: Lưu thông tin vào session nếu đúng
5. **Flash message**: Hiển thị thông báo lỗi nếu sai

#### **3. Trang Upload (/upload)**
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
            
            # Validate dữ liệu
            if not fullname.strip():
                return jsonify({'success': False, 'error': 'Tên không được để trống'})
            
            # Thêm người dùng vào database
            user_id = db.add_user(fullname, email, phone, department)
            
            # Xử lý ảnh upload
            uploaded_files = request.files.getlist('images')
            saved_paths = []
            
            for file in uploaded_files:
                if file and file.filename:
                    # Kiểm tra định dạng file
                    if not allowed_file(file.filename):
                        continue
                    
                    # Tạo tên file an toàn
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 
                                           f"{user_id}_{filename}")
                    
                    # Lưu file
                    file.save(file_path)
                    saved_paths.append(file_path)
            
            return jsonify({
                'success': True,
                'message': f'Đã lưu {len(saved_paths)} ảnh cho {fullname}',
                'user_id': user_id
            })
            
        except Exception as e:
            logging.error(f"Lỗi upload: {e}")
            return jsonify({'success': False, 'error': str(e)})
    
    return render_template('upload.html')
```

**Giải thích từng bước:**

1. **@login_required**: Yêu cầu đăng nhập
2. **GET request**: Hiển thị form upload
3. **POST request**: Xử lý upload
4. **Validate dữ liệu**: Kiểm tra tên không được trống
5. **Thêm user**: Lưu thông tin vào database
6. **Xử lý ảnh**: 
   - Kiểm tra định dạng file
   - Tạo tên file an toàn
   - Lưu file vào thư mục
7. **Return JSON**: Trả về kết quả cho AJAX

#### **4. Trang Xem Điểm Danh (/attendance)**
```python
@app.route('/attendance')
@login_required
def attendance():
    """Xem dữ liệu điểm danh"""
    try:
        # Lấy dữ liệu từ Google Sheets
        attendance_data = get_google_sheets_data()
        
        if attendance_data is not None and not attendance_data.empty:
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
        logging.error(f"Lỗi lấy dữ liệu điểm danh: {e}")
        return jsonify({'error': str(e)})
```

**Giải thích:**

1. **@login_required**: Yêu cầu đăng nhập
2. **Lấy dữ liệu**: Từ Google Sheets
3. **Chuyển đổi format**: DataFrame → JSON
4. **Return JSON**: Cho AJAX request
5. **Error handling**: Trả về error message nếu có lỗi

#### **5. Trang Tạo QR Code (/qr)**
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
            
            # Validate dữ liệu
            if not guest_name.strip() or not recipient_email.strip():
                return jsonify({'success': False, 'error': 'Vui lòng điền đầy đủ thông tin'})
            
            # Tạo thông tin khách
            guest_info = {
                'name': guest_name,
                'email': recipient_email,
                'visit_date': visit_date,
                'qr_id': str(uuid.uuid4())  # Tạo ID duy nhất
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
                'message': f'Đã gửi QR code cho {guest_name}',
                'qr_id': guest_info['qr_id']
            })
            
        except Exception as e:
            logging.error(f"Lỗi tạo QR code: {e}")
            return jsonify({'success': False, 'error': str(e)})
    
    return render_template('qr.html')
```

**Giải thích từng bước:**

1. **@login_required**: Yêu cầu đăng nhập
2. **GET request**: Hiển thị form tạo QR
3. **POST request**: Xử lý tạo QR code
4. **Validate dữ liệu**: Kiểm tra thông tin bắt buộc
5. **Tạo guest info**: Dictionary chứa thông tin khách
6. **Tạo QR code**: Sử dụng thư viện qrcode
7. **Gửi email**: Gọi hàm send_qr_email
8. **Return JSON**: Trả về kết quả cho AJAX

#### **6. Trang Quét QR Code (/scan_qr)**
```python
@app.route('/scan_qr', methods=['GET', 'POST'])
@login_required
def scan_qr():
    """Quét QR code để điểm danh"""
    if request.method == 'POST':
        try:
            # Lấy dữ liệu QR từ request
            qr_data = request.json.get('qr_data')
            
            if not qr_data:
                return jsonify({'success': False, 'error': 'Không có dữ liệu QR'})
            
            # Parse QR data
            guest_info = json.loads(qr_data)
            
            # Kiểm tra thông tin
            guest_name = guest_info.get('name')
            visit_date = guest_info.get('visit_date')
            qr_id = guest_info.get('qr_id')
            
            if not all([guest_name, visit_date, qr_id]):
                return jsonify({'success': False, 'error': 'QR code không hợp lệ'})
            
            # Kiểm tra ngày thăm
            today = datetime.now().strftime('%Y-%m-%d')
            if visit_date != today:
                return jsonify({'success': False, 'error': 'QR code không đúng ngày'})
            
            # Ghi điểm danh
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Lưu vào database
            db.add_attendance_record(None, timestamp, "QR", 100.0)
            
            # Lưu vào Google Sheets
            try:
                gc = gspread.service_account(filename='credentials/face-attendance.json')
                sheet = gc.open("Attendance").sheet1
                sheet.append_row([timestamp, guest_name, "QR", "100.0"])
            except Exception as e:
                logging.error(f"Lỗi lưu Google Sheets: {e}")
            
            return jsonify({
                'success': True,
                'message': f'Đã điểm danh thành công cho {guest_name}',
                'guest_name': guest_name
            })
            
        except Exception as e:
            logging.error(f"Lỗi quét QR: {e}")
            return jsonify({'success': False, 'error': str(e)})
    
    return render_template('scan_qr.html')
```

**Giải thích từng bước:**

1. **@login_required**: Yêu cầu đăng nhập
2. **GET request**: Hiển thị trang quét QR
3. **POST request**: Xử lý dữ liệu QR
4. **Parse QR data**: Chuyển đổi JSON string thành object
5. **Validate thông tin**: Kiểm tra đầy đủ thông tin
6. **Kiểm tra ngày**: QR code chỉ hợp lệ trong ngày
7. **Ghi điểm danh**: 
   - Lưu vào database
   - Lưu vào Google Sheets
8. **Return kết quả**: Thông báo thành công/thất bại

#### **7. Trang Đăng Xuất (/logout)**
```python
@app.route('/logout')
def logout():
    """Đăng xuất"""
    session.clear()
    return redirect(url_for('login'))
```

**Giải thích:**

- **`session.clear()`**: Xóa toàn bộ session
- **Redirect**: Chuyển về trang login

### **Helper Functions**

#### **1. Kiểm Tra File Upload**
```python
def allowed_file(filename):
    """Kiểm tra định dạng file được phép"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
```

**Giải thích:**

- **`ALLOWED_EXTENSIONS`**: Các định dạng file được phép upload
- **Kiểm tra extension**: Tách tên file và kiểm tra phần mở rộng
- **Case insensitive**: Chuyển về lowercase để so sánh

#### **2. Lưu Ảnh Khuôn Mặt**
```python
def save_face_images(user_id, uploaded_files):
    """Lưu ảnh khuôn mặt cho user"""
    saved_paths = []
    
    for file in uploaded_files:
        if file and file.filename:
            # Kiểm tra định dạng
            if not allowed_file(file.filename):
                continue
            
            # Tạo tên file an toàn
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], 
                                   f"{user_id}_{filename}")
            
            try:
                # Lưu file
                file.save(file_path)
                saved_paths.append(file_path)
                
                # Thêm vào database
                db.add_face_profile(user_id, file_path, None)
                
            except Exception as e:
                logging.error(f"Lỗi lưu file {filename}: {e}")
    
    return saved_paths
```

**Giải thích từng bước:**

1. **Kiểm tra file**: Đảm bảo file tồn tại và có tên
2. **Validate format**: Kiểm tra định dạng được phép
3. **Tạo tên an toàn**: Sử dụng `secure_filename()`
4. **Lưu file**: Ghi file vào thư mục
5. **Thêm database**: Lưu thông tin vào face_profiles table
6. **Error handling**: Log lỗi nếu có
7. **Return paths**: Trả về danh sách đường dẫn đã lưu

#### **3. Gửi Email QR Code**
```python
def send_qr_email(recipient_email, guest_name, qr_image_bytes, guest_info):
    """Gửi email chứa QR code"""
    try:
        # Cấu hình email
        msg = MIMEMultipart()
        msg['From'] = 'your-email@gmail.com'
        msg['To'] = recipient_email
        msg['Subject'] = f'QR Code Điểm Danh - {guest_name}'
        
        # Nội dung email
        body = f"""
        Xin chào {guest_name},
        
        Đây là QR code để điểm danh vào ngày {guest_info['visit_date']}.
        
        Vui lòng trình QR code này khi đến để được điểm danh.
        
        Trân trọng,
        Hệ thống điểm danh
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Đính kèm QR code
        attachment = MIMEImage(qr_image_bytes)
        attachment.add_header('Content-Disposition', 'attachment', 
                            filename=f'qr_code_{guest_name}.png')
        msg.attach(attachment)
        
        # Gửi email
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login('your-email@gmail.com', 'your-app-password')
        text = msg.as_string()
        server.sendmail('your-email@gmail.com', recipient_email, text)
        server.quit()
        
        logging.info(f"Đã gửi email QR code cho {guest_name}")
        
    except Exception as e:
        logging.error(f"Lỗi gửi email: {e}")
        raise
```

**Giải thích từng bước:**

1. **Cấu hình email**: Tạo MIMEMultipart message
2. **Thông tin email**: From, To, Subject
3. **Nội dung**: Text body với thông tin khách
4. **Đính kèm QR**: Tạo MIMEImage attachment
5. **SMTP setup**: Kết nối Gmail SMTP
6. **Gửi email**: Sử dụng SMTP để gửi
7. **Error handling**: Log lỗi nếu có

### **Error Handlers**

#### **1. 404 Error Handler**
```python
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404
```

#### **2. 500 Error Handler**
```python
@app.errorhandler(500)
def internal_error(error):
    db.conn.rollback()  # Rollback database transaction
    return render_template('500.html'), 500
```

**Giải thích:**

- **404 handler**: Trang không tìm thấy
- **500 handler**: Lỗi server, rollback database

### **Main Entry Point**
```python
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

**Giải thích:**

- **`debug=True`**: Chế độ debug cho development
- **`host='0.0.0.0'`**: Lắng nghe tất cả IP
- **`port=5000`**: Port mặc định của Flask

---

**Đây là phân tích chi tiết phần 3 - Web Application. Phần này chứa toàn bộ logic web interface và API endpoints.** 🎯 