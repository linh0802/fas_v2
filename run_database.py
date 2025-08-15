#!/usr/bin/env python3
"""
File khởi động cho quản lý database
Sử dụng package database đã được tổ chức
"""

import sys
import os

# Thêm thư mục hiện tại vào path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import fix_db, export_users, reset_db, manage_users

def show_database_info():
    """Hiển thị thông tin database hiện tại"""
    import sqlite3
    
    # Kiểm tra các đường dẫn database có thể có
    possible_paths = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "database", "database.db"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db"),
        "database.db"
    ]
    
    print("🔍 KIỂM TRA DATABASE")
    print("=" * 50)
    
    found_db = None
    for path in possible_paths:
        if os.path.exists(path):
            print(f"✅ Tìm thấy database: {path}")
            found_db = path
        else:
            print(f"❌ Không tìm thấy: {path}")
    
    if not found_db:
        print("\n❌ Không tìm thấy database nào!")
        return
    
    print(f"\n📊 THÔNG TIN DATABASE: {found_db}")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect(found_db)
        cur = conn.cursor()
        
        # Kiểm tra bảng users
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if cur.fetchone():
            cur.execute("SELECT COUNT(*) FROM users")
            total_users = cur.fetchone()[0]
            print(f"👥 Tổng users: {total_users}")
            
            # Hiển thị danh sách users
            cur.execute("SELECT user_id, username, full_name FROM users ORDER BY user_id")
            users = cur.fetchall()
            
            if users:
                print("\n📋 DANH SÁCH USERS:")
                print("-" * 50)
                print(f"{'ID':<5} | {'Username':<15} | {'Full Name':<20}")
                print("-" * 50)
                for user in users:
                    user_id, username, full_name = user
                    full_name = full_name or username
                    print(f"{user_id:<5} | {username:<15} | {full_name:<20}")
            else:
                print("⚠️  Không có users nào trong database")
        else:
            print("❌ Bảng 'users' không tồn tại")
        
        # Kiểm tra bảng face_profiles
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='face_profiles'")
        if cur.fetchone():
            cur.execute("SELECT COUNT(*) FROM face_profiles")
            total_images = cur.fetchone()[0]
            print(f"\n📸 Tổng ảnh: {total_images}")
            
            # Users có ảnh
            cur.execute("""
                SELECT u.user_id, u.username, COUNT(fp.profile_id) as image_count
                FROM users u
                LEFT JOIN face_profiles fp ON u.user_id = fp.user_id
                GROUP BY u.user_id
                HAVING COUNT(fp.profile_id) > 0
                ORDER BY u.user_id
            """)
            users_with_images = cur.fetchall()
            
            if users_with_images:
                print(f"✅ Users có ảnh: {len(users_with_images)}")
                print("\n📋 USERS CÓ ẢNH:")
                print("-" * 40)
                for user in users_with_images:
                    print(f"User {user[0]}: {user[1]} ({user[2]} ảnh)")
            else:
                print("⚠️  Không có user nào có ảnh")
        else:
            print("❌ Bảng 'face_profiles' không tồn tại")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Lỗi khi đọc database: {e}")

if __name__ == '__main__':
    print("🗄️  DATABASE MANAGEMENT")
    print("=" * 50)
    print("1. Sửa lỗi database")
    print("2. Xuất dữ liệu users ra CSV")
    print("3. Reset database")
    print("4. Hiển thị thông tin database")
    print("5. Quản lý users (xóa user, đổi mật khẩu)")
    print("6. Thoát")
    
    choice = input("\nChọn (1-6): ").strip()
    
    if choice == '1':
        fix_db()
    elif choice == '2':
        export_users()
    elif choice == '3':
        reset_db()
    elif choice == '4':
        show_database_info()
    elif choice == '5':
        manage_users()
    elif choice == '6':
        print("👋 Tạm biệt!")
    else:
        print("❌ Lựa chọn không hợp lệ") 