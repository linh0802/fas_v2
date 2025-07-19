# File khởi động ứng dụng GUI sử dụng package gui_modules
# Tất cả các module GUI đã được tổ chức trong thư mục gui_modules

import sys
import os

# Thêm thư mục hiện tại vào path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import từ package gui_modules
from gui_modules import AttendanceGUI

if __name__ == '__main__':
    if sys.platform.startswith('win'):
        import multiprocessing
        multiprocessing.freeze_support()
        
    app = AttendanceGUI()
    app.mainloop() 