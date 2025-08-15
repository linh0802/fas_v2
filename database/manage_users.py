#!/usr/bin/env python3
"""
Script quản lý users - thêm, sửa, xóa users
"""

import sqlite3
import os
import shutil
import sys

# Thêm thư mục cha vào path để import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_database_path, get_images_path

def show_all_users():
    """Hiển thị tất cả users"""
    DB_PATH = get_database_path()
    
    print("👥 DANH SÁCH TẤT CẢ USERS")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Lấy thông tin users và số lượng ảnh
    cur.execute("""
        SELECT u.user_id, u.username, u.full_name, u.password, COUNT(fp.profile_id) as image_count
        FROM users u
        LEFT JOIN face_profiles fp ON u.user_id = fp.user_id
        GROUP BY u.user_id
        ORDER BY u.user_id
    """)
    users = cur.fetchall()
    conn.close()
    
    print(f"{'ID':<5} | {'Username':<15} | {'Full Name':<20} | {'Password':<10} | {'Ảnh':<5}")
    print("-" * 70)
    for user in users:
        user_id, username, full_name, password, image_count = user
        full_name = full_name or username
        print(f"{user_id:<5} | {username:<15} | {full_name:<20} | {password:<10} | {image_count:<5}")

def delete_user(user_id):
    """Xóa user và tất cả dữ liệu liên quan"""
    DB_PATH = get_database_path()
    IMAGES_PATH = get_images_path()
    
    print(f"🗑️  XÓA USER_{user_id}")
    print("=" * 50)
    
    # Kiểm tra user có tồn tại không
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id, username, full_name FROM users WHERE user_id = ?", (user_id,))
    user = cur.fetchone()
    
    if not user:
        print(f"❌ Không tìm thấy user_{user_id}!")
        conn.close()
        return False
    
    user_id, username, full_name = user
    print(f"👤 User: {username} ({full_name})")
    
    # Đếm số ảnh
    cur.execute("SELECT COUNT(*) FROM face_profiles WHERE user_id = ?", (user_id,))
    image_count = cur.fetchone()[0]
    print(f"📸 Số ảnh: {image_count}")
    
    # Xác nhận xóa
    print(f"\n⚠️  CẢNH BÁO: Việc xóa user này sẽ:")
    print(f"   - Xóa user '{username}' khỏi database")
    print(f"   - Xóa {image_count} ảnh khỏi database")
    print(f"   - Xóa thư mục ảnh: user_{user_id}")
    print(f"   - KHÔNG THỂ KHÔI PHỤC!")
    
    confirm = input(f"\nBạn có chắc chắn muốn xóa user '{username}'? (y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ Đã hủy bỏ!")
        conn.close()
        return False
    
    try:
        # Xóa ảnh từ database
        cur.execute("DELETE FROM face_profiles WHERE user_id = ?", (user_id,))
        deleted_images = cur.rowcount
        print(f"✅ Đã xóa {deleted_images} ảnh khỏi database")
        
        # Xóa user
        cur.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        if cur.rowcount > 0:
            print(f"✅ Đã xóa user '{username}' khỏi database")
        else:
            print("❌ Không thể xóa user!")
            conn.rollback()
            conn.close()
            return False
        
        # Xóa thư mục ảnh
        user_dir = os.path.join(IMAGES_PATH, f"user_{user_id}")
        if os.path.exists(user_dir):
            shutil.rmtree(user_dir)
            print(f"✅ Đã xóa thư mục: {user_dir}")
        else:
            print(f"⚠️  Thư mục không tồn tại: {user_dir}")
        
        conn.commit()
        print(f"🎉 Đã xóa thành công user '{username}' và tất cả dữ liệu liên quan!")
        return True
        
    except Exception as e:
        print(f"❌ Lỗi khi xóa user: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def change_user_password(user_id, new_password):
    """Thay đổi mật khẩu cho user"""
    DB_PATH = get_database_path()
    
    print(f"🔐 THAY ĐỔI MẬT KHẨU CHO USER_{user_id}")
    print("=" * 50)
    
    # Kiểm tra user có tồn tại không
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id, username, full_name FROM users WHERE user_id = ?", (user_id,))
    user = cur.fetchone()
    
    if not user:
        print(f"❌ Không tìm thấy user_{user_id}!")
        conn.close()
        return False
    
    user_id, username, full_name = user
    print(f"👤 User: {username} ({full_name})")
    print(f"🔑 Mật khẩu mới: {new_password}")
    
    # Thay đổi mật khẩu
    cur.execute("UPDATE users SET password = ? WHERE user_id = ?", (new_password, user_id))
    conn.commit()
    conn.close()
    
    print("✅ Đã thay đổi mật khẩu thành công!")
    return True

def add_user():
    """Thêm user mới"""
    DB_PATH = get_database_path()
    
    print("➕ THÊM USER MỚI")
    print("=" * 50)
    
    # Nhập thông tin user
    username = input("Nhập username: ").strip()
    if not username:
        print("❌ Username không được để trống!")
        return False
    
    # Kiểm tra username có ký tự đặc biệt không
    if not username.replace('_', '').replace('-', '').isalnum():
        print("❌ Username chỉ được chứa chữ cái, số, dấu gạch dưới (_) và dấu gạch ngang (-)")
        return False
    
    # Kiểm tra độ dài username
    if len(username) < 3:
        print("❌ Username phải có ít nhất 3 ký tự!")
        return False
    
    if len(username) > 20:
        print("❌ Username không được quá 20 ký tự!")
        return False
    
    full_name = input("Nhập họ tên đầy đủ: ").strip()
    if not full_name:
        print("❌ Họ tên không được để trống!")
        return False
    
    # Kiểm tra độ dài họ tên
    if len(full_name) < 2:
        print("❌ Họ tên phải có ít nhất 2 ký tự!")
        return False
    
    if len(full_name) > 50:
        print("❌ Họ tên không được quá 50 ký tự!")
        return False
    
    password = input("Nhập mật khẩu: ").strip()
    if not password:
        print("❌ Mật khẩu không được để trống!")
        return False
    
    # Kiểm tra độ dài mật khẩu
    if len(password) < 4:
        print("❌ Mật khẩu phải có ít nhất 4 ký tự!")
        return False
    
    # Xác nhận thông tin
    print(f"\n📋 THÔNG TIN USER MỚI:")
    print(f"👤 Username: {username}")
    print(f"👤 Họ tên: {full_name}")
    print(f"🔑 Mật khẩu: {password}")
    
    confirm = input(f"\nBạn có chắc chắn muốn thêm user này? (y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ Đã hủy bỏ!")
        return False
    
    # Kiểm tra username đã tồn tại chưa
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE username = ?", (username,))
    existing_user = cur.fetchone()
    
    if existing_user:
        print(f"❌ Username '{username}' đã tồn tại!")
        conn.close()
        return False
    
    try:
        # Thêm user mới
        cur.execute(
            "INSERT INTO users (username, full_name, password) VALUES (?, ?, ?)",
            (username, full_name, password)
        )
        
        user_id = cur.lastrowid
        conn.commit()
        
        print(f"\n✅ Đã thêm user thành công!")
        print(f"👤 User ID: {user_id}")
        print(f"👤 Username: {username}")
        print(f"👤 Họ tên: {full_name}")
        print(f"🔑 Mật khẩu: {password}")
        
        # Tạo thư mục ảnh cho user mới
        IMAGES_PATH = get_images_path()
        user_dir = os.path.join(IMAGES_PATH, f"user_{user_id}")
        os.makedirs(user_dir, exist_ok=True)
        print(f"📁 Đã tạo thư mục ảnh: {user_dir}")
        
        print(f"\n💡 Lưu ý: User '{username}' đã sẵn sàng để thêm ảnh khuôn mặt!")
        
        return True
        
    except Exception as e:
        print(f"❌ Lỗi khi thêm user: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def show_user_details(user_id):
    """Hiển thị thông tin chi tiết của một user"""
    DB_PATH = get_database_path()
    
    print(f"👤 THÔNG TIN CHI TIẾT USER_{user_id}")
    print("=" * 50)
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Lấy thông tin user
    cur.execute("""
        SELECT u.user_id, u.username, u.full_name, u.password, 
               COUNT(fp.profile_id) as image_count
        FROM users u
        LEFT JOIN face_profiles fp ON u.user_id = fp.user_id
        WHERE u.user_id = ?
        GROUP BY u.user_id
    """, (user_id,))
    
    user = cur.fetchone()
    
    if not user:
        print(f"❌ Không tìm thấy user_{user_id}!")
        conn.close()
        return False
    
    user_id, username, full_name, password, image_count = user
    
    print(f"🆔 User ID: {user_id}")
    print(f"👤 Username: {username}")
    print(f"👤 Họ tên: {full_name or 'Chưa có'}")
    print(f"🔑 Mật khẩu: {password}")
    print(f"📸 Số lượng ảnh: {image_count}")
    
    if image_count > 0:
        # Kiểm tra thư mục ảnh
        IMAGES_PATH = get_images_path()
        user_dir = os.path.join(IMAGES_PATH, f"user_{user_id}")
        if os.path.exists(user_dir):
            actual_files = len([f for f in os.listdir(user_dir) 
                              if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
            print(f"📁 Thư mục ảnh: {user_dir}")
            print(f"📁 Số file thực tế: {actual_files}")
            
            if actual_files != image_count:
                print(f"⚠️  Cảnh báo: Số ảnh trong DB ({image_count}) khác với số file thực tế ({actual_files})")
        else:
            print(f"❌ Thư mục ảnh không tồn tại: {user_dir}")
    else:
        print("📸 Chưa có ảnh nào")
    
    conn.close()
    return True

def manage_users():
    """Menu chính quản lý users"""
    print("👥 QUẢN LÝ USERS")
    print("=" * 50)
    
    while True:
        # Hiển thị danh sách users
        show_all_users()
        
        print("\n" + "=" * 50)
        print("1. Thêm user mới")
        print("2. Xem thông tin chi tiết user")
        print("3. Xóa user")
        print("4. Thay đổi mật khẩu")
        print("5. Thoát")
        
        choice = input("\nChọn (1-5): ").strip()
        
        if choice == '1':
            add_user()
            input("\nNhấn Enter để tiếp tục...")
            
        elif choice == '2':
            try:
                user_id = int(input("Nhập User ID cần xem: ").strip())
                show_user_details(user_id)
            except ValueError:
                print("❌ User ID phải là số!")
            except Exception as e:
                print(f"❌ Lỗi: {e}")
            input("\nNhấn Enter để tiếp tục...")
            
        elif choice == '3':
            try:
                user_id = int(input("Nhập User ID cần xóa: ").strip())
                result = delete_user(user_id)
                if result:
                    # Tự động export lại file CSV sau khi xóa user
                    from database.export_users_csv import export_users_to_csv
                    export_users_to_csv()
                    print("✅ Đã cập nhật lại file users_export.csv!")
            except ValueError:
                print("❌ User ID phải là số!")
            except Exception as e:
                print(f"❌ Lỗi: {e}")
            input("\nNhấn Enter để tiếp tục...")
                
        elif choice == '4':
            try:
                user_id = int(input("Nhập User ID: ").strip())
                new_password = input("Nhập mật khẩu mới: ").strip()
                
                if not new_password:
                    print("❌ Mật khẩu không được để trống!")
                    continue
                
                change_user_password(user_id, new_password)
                
            except ValueError:
                print("❌ User ID phải là số!")
            except Exception as e:
                print(f"❌ Lỗi: {e}")
            input("\nNhấn Enter để tiếp tục...")
                
        elif choice == '5':
            print("👋 Tạm biệt!")
            break
        else:
            print("❌ Lựa chọn không hợp lệ!")
            input("\nNhấn Enter để tiếp tục...")

if __name__ == "__main__":
    manage_users()
