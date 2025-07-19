#!/usr/bin/env python3
"""
Script sửa dữ liệu database bị sai.
Chức năng:
- Sửa mapping user_id và full_name
- Xóa ảnh không tồn tại
- Xóa ảnh duplicate
- Kiểm tra tính toàn vẹn dữ liệu
"""

import os
import sqlite3
import json
import sys
import os
# Thêm thư mục cha vào path để import các module khác
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from .db import get_user_id_to_fullname_mapping, get_db_connection

def show_database_status():
    """Hiển thị trạng thái database hiện tại."""
    print("🔍 TRẠNG THÁI DATABASE HIỆN TẠI")
    print("=" * 50)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Thống kê users
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM users WHERE full_name IS NULL OR full_name = ''")
    users_without_name = cur.fetchone()[0]
    
    # Thống kê ảnh
    cur.execute("SELECT COUNT(*) FROM face_profiles")
    total_images = cur.fetchone()[0]
    
    # Ảnh không tồn tại
    cur.execute("SELECT image_path FROM face_profiles")
    missing_images = []
    for row in cur.fetchall():
        if not os.path.exists(row['image_path']):
            missing_images.append(row['image_path'])
    
    # Ảnh duplicate
    cur.execute("SELECT image_path, COUNT(*) as count FROM face_profiles GROUP BY image_path HAVING count > 1")
    duplicates = cur.fetchall()
    
    conn.close()
    
    print(f"👥 Tổng users: {total_users}")
    print(f"⚠️  Users không có tên: {users_without_name}")
    print(f"📸 Tổng ảnh: {total_images}")
    print(f"❌ Ảnh không tồn tại: {len(missing_images)}")
    print(f"🔄 Ảnh duplicate: {len(duplicates)}")
    
    return {
        'total_users': total_users,
        'users_without_name': users_without_name,
        'total_images': total_images,
        'missing_images': missing_images,
        'duplicates': [d['image_path'] for d in duplicates]
    }

def fix_user_names():
    """Sửa users không có full_name."""
    print("\n🔧 SỬA USERS KHÔNG CÓ TÊN")
    print("=" * 40)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Lấy users không có full_name
    cur.execute("SELECT user_id, username FROM users WHERE full_name IS NULL OR full_name = ''")
    users_without_name = cur.fetchall()
    
    if not users_without_name:
        print("✅ Không có users nào thiếu tên")
        conn.close()
        return
    
    print(f"Tìm thấy {len(users_without_name)} users không có tên:")
    for user in users_without_name:
        print(f"  User ID {user['user_id']}: {user['username']}")
    
    print("\nNhập tên cho từng user (hoặc Enter để bỏ qua):")
    
    fixed_count = 0
    for user in users_without_name:
        user_id = user['user_id']
        username = user['username']
        
        # Gợi ý tên từ username
        suggested_name = username.replace('_', ' ').title()
        
        full_name = input(f"User {user_id} ({username}): [{suggested_name}] ").strip()
        if not full_name:
            full_name = suggested_name
        
        if full_name:
            cur.execute("UPDATE users SET full_name = ? WHERE user_id = ?", (full_name, user_id))
            fixed_count += 1
            print(f"  ✅ Đã cập nhật: {full_name}")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Đã sửa {fixed_count} users")

def fix_missing_images():
    """Xóa ảnh không tồn tại khỏi database."""
    print("\n🗑️  XÓA ẢNH KHÔNG TỒN TẠI")
    print("=" * 40)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Lấy ảnh không tồn tại
    cur.execute("SELECT profile_id, image_path FROM face_profiles")
    missing_records = []
    for row in cur.fetchall():
        if not os.path.exists(row['image_path']):
            missing_records.append(row)
    
    if not missing_records:
        print("✅ Không có ảnh nào không tồn tại")
        conn.close()
        return
    
    print(f"Tìm thấy {len(missing_records)} ảnh không tồn tại:")
    for record in missing_records[:5]:  # Chỉ hiển thị 5 ảnh đầu
        print(f"  - {record['image_path']}")
    
    if len(missing_records) > 5:
        print(f"  ... và {len(missing_records) - 5} ảnh khác")
    
    confirm = input("\nBạn có muốn xóa các ảnh này khỏi database? (y/N): ").strip().lower()
    
    if confirm == 'y':
        deleted_count = 0
        for record in missing_records:
            cur.execute("DELETE FROM face_profiles WHERE profile_id = ?", (record['profile_id'],))
            deleted_count += 1
        
        conn.commit()
        print(f"✅ Đã xóa {deleted_count} ảnh không tồn tại")
    else:
        print("❌ Đã hủy")
    
    conn.close()

def fix_duplicate_images():
    """Xóa ảnh duplicate khỏi database."""
    print("\n🔄 XÓA ẢNH DUPLICATE")
    print("=" * 40)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Lấy ảnh duplicate
    cur.execute("""
        SELECT image_path, COUNT(*) as count, GROUP_CONCAT(profile_id) as profile_ids
        FROM face_profiles 
        GROUP BY image_path 
        HAVING count > 1
    """)
    duplicates = cur.fetchall()
    
    if not duplicates:
        print("✅ Không có ảnh duplicate")
        conn.close()
        return
    
    print(f"Tìm thấy {len(duplicates)} ảnh duplicate:")
    for dup in duplicates[:5]:
        print(f"  - {dup['image_path']} ({dup['count']} lần)")
    
    if len(duplicates) > 5:
        print(f"  ... và {len(duplicates) - 5} ảnh khác")
    
    confirm = input("\nBạn có muốn xóa các ảnh duplicate? (y/N): ").strip().lower()
    
    if confirm == 'y':
        deleted_count = 0
        for dup in duplicates:
            profile_ids = dup['profile_ids'].split(',')
            # Giữ lại record đầu tiên, xóa các record còn lại
            for profile_id in profile_ids[1:]:
                cur.execute("DELETE FROM face_profiles WHERE profile_id = ?", (profile_id,))
                deleted_count += 1
        
        conn.commit()
        print(f"✅ Đã xóa {deleted_count} ảnh duplicate")
    else:
        print("❌ Đã hủy")
    
    conn.close()

def fix_user_mapping():
    """Sửa mapping user_id và full_name."""
    print("\n🔧 SỬA MAPPING USER_ID VÀ FULL_NAME")
    print("=" * 50)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Lấy tất cả users
    cur.execute("SELECT user_id, username, full_name FROM users ORDER BY user_id")
    users = cur.fetchall()
    
    print("📋 DANH SÁCH USERS HIỆN TẠI:")
    print("-" * 60)
    print(f"{'User ID':<8} | {'Username':<15} | {'Full Name':<25}")
    print("-" * 60)
    
    for user in users:
        user_id = user['user_id']
        username = user['username']
        full_name = user['full_name'] or "N/A"
        print(f"{user_id:<8} | {username:<15} | {full_name:<25}")
    
    print("\nChọn hành động:")
    print("1. Sửa tên một user cụ thể")
    print("2. Sửa tên tất cả users")
    print("3. Quay lại")
    
    choice = input("Nhập lựa chọn (1-3): ").strip()
    
    if choice == '1':
        user_id = input("Nhập User ID cần sửa: ").strip()
        try:
            user_id = int(user_id)
            cur.execute("SELECT username, full_name FROM users WHERE user_id = ?", (user_id,))
            user = cur.fetchone()
            
            if user:
                print(f"User hiện tại: {user['username']} - {user['full_name']}")
                new_name = input("Nhập tên mới: ").strip()
                if new_name:
                    cur.execute("UPDATE users SET full_name = ? WHERE user_id = ?", (new_name, user_id))
                    conn.commit()
                    print(f"✅ Đã cập nhật user {user_id}: {new_name}")
                else:
                    print("❌ Tên không được để trống")
            else:
                print(f"❌ Không tìm thấy user với ID {user_id}")
        except ValueError:
            print("❌ User ID phải là số")
    
    elif choice == '2':
        print("\nNhập tên mới cho từng user (Enter để giữ nguyên):")
        for user in users:
            user_id = user['user_id']
            username = user['username']
            current_name = user['full_name'] or username
            
            new_name = input(f"User {user_id} ({username}): [{current_name}] ").strip()
            if new_name:
                cur.execute("UPDATE users SET full_name = ? WHERE user_id = ?", (new_name, user_id))
                print(f"  ✅ Đã cập nhật: {new_name}")
        
        conn.commit()
        print("✅ Đã cập nhật tất cả users")
    
    conn.close()

def validate_training_data():
    """Kiểm tra tính hợp lệ của dữ liệu training."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    issues = []
    warnings = []
    
    # Kiểm tra users không có full_name
    cur.execute("SELECT user_id, username FROM users WHERE full_name IS NULL OR full_name = ''")
    users_without_name = cur.fetchall()
    if users_without_name:
        issues.append(f"Có {len(users_without_name)} users không có full_name")
    
    # Kiểm tra ảnh không tồn tại
    cur.execute("SELECT user_id, image_path FROM face_profiles")
    face_profiles = cur.fetchall()
    missing_images = []
    for profile in face_profiles:
        if not os.path.exists(profile['image_path']):
            missing_images.append(profile['image_path'])
    
    if missing_images:
        issues.append(f"Có {len(missing_images)} ảnh không tồn tại trên disk")
    
    # Kiểm tra duplicate image paths
    cur.execute("SELECT image_path, COUNT(*) as count FROM face_profiles GROUP BY image_path HAVING count > 1")
    duplicates = cur.fetchall()
    if duplicates:
        issues.append(f"Có {len(duplicates)} ảnh bị duplicate trong database")
    
    conn.close()
    
    return {
        'is_valid': len(issues) == 0,
        'issues': issues,
        'warnings': warnings,
        'missing_images': missing_images,
        'duplicate_images': [d['image_path'] for d in duplicates] if duplicates else []
    }

def export_fixed_data():
    """Export dữ liệu đã sửa."""
    print("\n📊 EXPORT DỮ LIỆU ĐÃ SỬA")
    print("=" * 40)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Lấy dữ liệu đã sửa
    cur.execute("""
        SELECT u.user_id, u.username, u.full_name, COUNT(fp.profile_id) as image_count
        FROM users u
        LEFT JOIN face_profiles fp ON u.user_id = fp.user_id
        GROUP BY u.user_id
        ORDER BY u.user_id
    """)
    
    data = []
    for row in cur.fetchall():
        data.append({
            'user_id': row['user_id'],
            'username': row['username'],
            'full_name': row['full_name'],
            'image_count': row['image_count']
        })
    
    conn.close()
    
    # Lưu ra file
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixed_database_export.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Đã export {len(data)} users ra file: {json_path}")
    
    # Tạo mapping cho training
    mapping = {}
    for user in data:
        if user['image_count'] > 0:
            mapping[str(user['user_id'])] = user['full_name']
    
    mapping_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'user_id_to_fullname_fixed.json')
    with open(mapping_path, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Đã tạo mapping cho {len(mapping)} users có ảnh: {mapping_path}")

def main():
    """Menu chính."""
    print("🔧 CÔNG CỤ SỬA DỮ LIỆU DATABASE")
    print("=" * 60)
    
    while True:
        print("\n📋 MENU:")
        print("1. Xem trạng thái database")
        print("2. Sửa users không có tên")
        print("3. Xóa ảnh không tồn tại")
        print("4. Xóa ảnh duplicate")
        print("5. Sửa mapping user_id và full_name")
        print("6. Export dữ liệu đã sửa")
        print("7. Kiểm tra tính hợp lệ")
        print("8. Thoát")
        
        choice = input("\nNhập lựa chọn (1-8): ").strip()
        
        if choice == '1':
            show_database_status()
        
        elif choice == '2':
            fix_user_names()
        
        elif choice == '3':
            fix_missing_images()
        
        elif choice == '4':
            fix_duplicate_images()
        
        elif choice == '5':
            fix_user_mapping()
        
        elif choice == '6':
            export_fixed_data()
        
        elif choice == '7':
            print("\n🔍 KIỂM TRA TÍNH HỢP LỆ")
            print("=" * 40)
            validation = validate_training_data()
            
            if validation['is_valid']:
                print("✅ Dữ liệu hợp lệ!")
            else:
                print("❌ Dữ liệu có vấn đề:")
                for issue in validation['issues']:
                    print(f"  - {issue}")
            
            if validation['warnings']:
                print("\n⚠️  Cảnh báo:")
                for warning in validation['warnings']:
                    print(f"  - {warning}")
        
        elif choice == '8':
            print("👋 Tạm biệt!")
            break
        
        else:
            print("❌ Lựa chọn không hợp lệ")

if __name__ == "__main__":
    main() 