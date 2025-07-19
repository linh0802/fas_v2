# Hệ Thống Điểm Danh Khuôn Mặt - FaceAttendance

## Giới thiệu
Hệ thống điểm danh khuôn mặt FaceAttendance là một giải pháp AI/IoT tích hợp, giúp tự động nhận diện, quản lý và lưu trữ thông tin điểm danh bằng khuôn mặt. Hệ thống hỗ trợ giao diện người dùng trực quan (Tkinter), backend API (Flask), đồng bộ dữ liệu với Google Sheets, hỗ trợ mã QR, cảm biến chuyển động PIR, và nhiều tính năng nâng cao khác.

> **Xem chi tiết pipeline AI, giải thích học thuật, bảng so sánh... tại [TECHNICAL_DETAILS.md](./TECHNICAL_DETAILS.md)**

## Kiến trúc tổng thể
- **Giao diện người dùng (Tkinter, chia module):** Quản lý, thêm mới, điểm danh, xem dữ liệu, huấn luyện lại model. Các frame riêng biệt: Nhận diện, Thêm người, Dữ liệu.
- **Nhận diện khuôn mặt (AI):** DeepFace, Facenet, MTCNN, anti-spoofing, nhận diện real-time.
- **Quản lý dữ liệu:** Lưu trữ SQLite3, đồng bộ Google Sheets, xuất/nhập CSV.
- **Web backend (Flask):** API điểm danh, quản lý người dùng, upload ảnh, xác thực, gửi email QR.
- **Tối ưu hiệu suất:** batch_size nhỏ, giới hạn luồng OpenCV, sleep trong train, hiển thị CPU/RAM usage trên GUI.

## Cấu trúc thư mục chính
- `gui_modules/`: Các module giao diện (RecognitionFrame, DataEntryFrame, AttendanceDataFrame, ...)
- `core/`: Nhận diện, anti-spoofing, TTS, cảm biến PIR
- `database/`: Quản lý database, xuất/nhập CSV, reset, fix lỗi
- `training/`: Script train, kiểm tra dữ liệu, sinh embedding
- `web_app/`: Backend Flask, API, xác thực, upload ảnh, gửi email QR
- `models/`: Model AI, label encoder
- `images_attendance/`: Ảnh gốc
- `processed_faces/`: Ảnh đã cắt mặt
- `logs/`, `training.log`: Log hệ thống, log train
- `requirements.txt`, `.gitignore`, `README.md`

## Các tính năng chính
- **Nhận diện khuôn mặt real-time** với AI, chống giả mạo (anti-spoofing).
- **Thêm người mới**: Tự động nhận diện tên, chụp ảnh, lưu vào DB, kiểm tra trùng lặp.
- **Điểm danh tự động**: Giao diện trực quan, log chi tiết, phát âm tên, lưu lịch sử.
- **Huấn luyện lại mô hình**: Tự động trích xuất khuôn mặt, sinh embedding, cập nhật model.
- **Quản lý dữ liệu**: Xem, xuất, nhập, đồng bộ dữ liệu người dùng và ảnh.
- **API backend**: Cung cấp dữ liệu điểm danh, xác thực, upload ảnh, gửi email QR.
- **Đồng bộ Google Sheets**: Lưu lịch sử điểm danh lên cloud, hỗ trợ offline sync.
- **Tích hợp cảm biến PIR**: Tự động bật/tắt nhận diện khi có chuyển động.
- **Hỗ trợ mã QR**: Đăng ký khách, gửi email QR, xác nhận điểm danh qua QR.
- **Phát âm tên (TTS)**: Thông báo trạng thái, cảnh báo, xác nhận.
- **Logging chuyên sâu**: Ghi log hệ thống, log huấn luyện, log điểm danh.

## Hướng dẫn cài đặt & sử dụng
### 1. Yêu cầu hệ thống
- **Phần cứng:** Raspberry Pi 4/5 hoặc PC, webcam, cảm biến PIR (tùy chọn), loa (TTS), internet.
- **Phần mềm:** Python 3.8+, pip, các thư viện trong `requirements.txt`.

### 2. Cài đặt
```bash
# Clone mã nguồn
$ git clone <repo_url>
$ cd faceattendance

# Tạo môi trường ảo (khuyến nghị)
$ python3 -m venv .venv
$ source .venv/bin/activate

# Cài đặt thư viện
$ pip install -r requirements.txt

# Khởi tạo database (chỉ lần đầu)
$ python database/db.py

# Chạy backend Flask (API)
$ python web_app/app.py

# Chạy giao diện người dùng (GUI)
$ python gui_modules/gui_main.py
```

### 3. Cấu hình Google Sheets, Email, Ngrok
- Đặt file credentials Google API vào `credentials/face-attendance.json`.
- Cấu hình biến môi trường email, ngrok nếu dùng tính năng gửi QR/email/điểm danh từ xa.

## Hướng dẫn sử dụng
- **Thêm người mới:** Vào giao diện, nhập/tự động nhận diện tên, chụp ảnh, lưu, huấn luyện lại model.
- **Điểm danh:** Chọn tab nhận diện, hệ thống tự động nhận diện, log, phát âm tên, lưu lịch sử.
- **Xem dữ liệu:** Tab dữ liệu điểm danh, có thể xuất CSV, xem log, lọc dữ liệu.
- **Huấn luyện lại:** Sau khi thêm người mới, nhấn "Huấn luyện" để cập nhật model.
- **Quản lý ảnh:** Ảnh lưu tại `images_attendance/`, embedding tại `models/`.
- **API:** Truy cập các endpoint Flask để lấy dữ liệu, upload ảnh, xác thực, v.v.

## Các file/thư mục quan trọng
- `gui_modules/gui_main.py`: Giao diện chính, quản lý toàn bộ luồng GUI.
- `gui_modules/recognition_frame.py`, `gui_modules/data_entry_frame.py`, ...: Các frame giao diện (nhận diện, thêm người, dữ liệu...)
- `core/recognition_class.py`, `core/recognition_simple.py`, `core/smart_tts.py`, ...: Nhận diện khuôn mặt, anti-spoofing, TTS, cảm biến PIR.
- `database/db.py`, `database/export_users_csv.py`, `database/reset_database.py`, ...: Quản lý database, xuất/nhập CSV, reset, fix lỗi.
- `training/finish_train.py`, `training/check_training_data.py`: Script train, kiểm tra dữ liệu, sinh embedding.
- `web_app/app.py`: Backend Flask, API, xác thực, upload ảnh, gửi email QR.
- `models/`: Model AI, label encoder.
- `images_attendance/`: Ảnh gốc.
- `processed_faces/`: Ảnh đã cắt mặt.
- `logs/`, `training.log`: Log hệ thống, log train.
- `requirements.txt`, `.gitignore`, `README.md`

## Cấu trúc thư mục (Cập nhật 2024)
```
faceattendance/
├── core/
│   ├── recognition_class.py
│   ├── recognition_simple.py
│   └── ...
├── database/
│   ├── db.py
│   ├── export_users_csv.py
│   ├── reset_database.py
│   └── ...
├── gui_modules/
│   ├── gui_main.py
│   ├── recognition_frame.py
│   ├── data_entry_frame.py
│   └── ...
├── training/
│   ├── finish_train.py
│   ├── check_training_data.py
│   └── ...
├── web_app/
│   └── app.py
├── models/
├── images_attendance/
├── processed_faces/
├── logs/
├── requirements.txt
├── .gitignore
└── README.md
```

## Hướng dẫn chạy
```bash
# Chạy giao diện người dùng (GUI)
$ python gui_modules/gui_main.py

# Hoặc dùng script khởi động nếu có
$ python run_gui_modular.py

# Chạy backend Flask (API)
$ python web_app/app.py

# Khởi tạo database (chỉ lần đầu)
$ python database/db.py

# Huấn luyện lại model
$ python training/finish_train.py --smart
```

## Yêu cầu phần mềm/phần cứng
- Python >= 3.8, pip
- Raspberry Pi 4/5 hoặc PC, webcam, loa, cảm biến PIR (tùy chọn)
- Kết nối internet để đồng bộ cloud, gửi email, Google Sheets

## Tài liệu tham khảo
- [DeepFace](https://github.com/serengil/deepface)
- [Facenet-pytorch](https://github.com/timesler/facenet-pytorch)
- [Flask](https://flask.palletsprojects.com/)
- [Google Sheets API](https://developers.google.com/sheets/api)
- [Tkinter](https://docs.python.org/3/library/tkinter.html)
- [OpenCV](https://opencv.org/)
