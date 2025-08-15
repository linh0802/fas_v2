import os
import logging
from datetime import datetime
import sys

# Thêm thư mục cha vào path để import các module khác
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Tạo thư mục logs nếu chưa có
os.makedirs('logs', exist_ok=True)

# Tạo tên file log duy nhất cho toàn bộ phiên làm việc
LOG_FILENAME = datetime.now().strftime('logs/face_recognition_%Y%m%d_%H%M%S.log')

# Cấu hình logging
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# Xóa tất cả handler cũ (nếu có)
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

file_handler = logging.FileHandler(LOG_FILENAME, encoding='utf-8')
file_handler.setFormatter(formatter)
root_logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
root_logger.addHandler(console_handler)

# Ẩn log DEBUG của urllib3 và requests
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)

# Đường dẫn các file/script
TRAIN_SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'training', 'finish_train.py')
API_ATTENDANCE_URL = 'http://127.0.0.1:5000/api/attendance'
WEB_APP_SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'web_app', 'app.py')

# Màu sắc giao diện
DARK_BG = '#181a20'
DARK_PANEL = '#23272f'
DARK_ACCENT = '#00bcd4'
DARK_TEXT = '#f1f1f1'
DARK_BTN = '#222c36'
DARK_BTN_HOVER = '#00bcd4'

# Cấu hình giao diện
WINDOW_WIDTH = 1020
WINDOW_HEIGHT = 590
WEBCAM_WIDTH = 640
WEBCAM_HEIGHT = 480
PREVIEW_WIDTH = 270
PREVIEW_HEIGHT = 360 