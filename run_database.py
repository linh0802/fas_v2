#!/usr/bin/env python3
"""
File khởi động cho quản lý database
Sử dụng package database đã được tổ chức
"""

import sys
import os

# Thêm thư mục hiện tại vào path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import fix_db, export_users, reset_db

if __name__ == '__main__':
    print("🗄️  DATABASE MANAGEMENT")
    print("=" * 50)
    print("1. Sửa lỗi database")
    print("2. Xuất dữ liệu users ra CSV")
    print("3. Reset database")
    print("4. Thoát")
    
    choice = input("\nChọn (1-4): ").strip()
    
    if choice == '1':
        fix_db()
    elif choice == '2':
        export_users()
    elif choice == '3':
        reset_db()
    elif choice == '4':
        print("👋 Tạm biệt!")
    else:
        print("❌ Lựa chọn không hợp lệ") 