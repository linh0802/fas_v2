#!/usr/bin/env python3
"""
File khởi động cho training model
Sử dụng package training đã được tổ chức
"""

import sys
import os

# Thêm thư mục hiện tại vào path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from training import train_model, check_data

if __name__ == '__main__':
    print("TRAINING SYSTEM")
    print("=" * 50)
    print("1. Kiểm tra dữ liệu training")
    print("2. Train model")
    print("3. Thoát")
    
    choice = input("\nChọn (1-3): ").strip()
    
    if choice == '1':
        check_data()
    elif choice == '2':
        train_model()
    elif choice == '3':
        print("Tạm biệt!")
    else:
        print("Lựa chọn không hợp lệ") 