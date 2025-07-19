#!/usr/bin/env python3
"""
Script kiểm tra dữ liệu training từ database.
Kiểm tra dữ liệu được thêm qua GUI và Web app.
"""

import os
import sys
import json
from datetime import datetime
import sys
import os
# Thêm thư mục cha vào path để import các module khác
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import (
    get_user_id_to_fullname_mapping,
    get_training_data_summary
)

def print_training_data_summary():
    """In ra tổng quan về dữ liệu training."""
    summary = get_training_data_summary()
    
    print("=" * 60)
    print("TỔNG QUAN DỮ LIỆU TRAINING")
    print("=" * 60)
    print(f"Tổng số users: {summary['total_users']}")
    print(f"Tổng số ảnh: {summary['total_images']}")
    print()
    
    print("DANH SÁCH USERS VÀ SỐ LƯỢNG ẢNH:")
    print("-" * 50)
    for user in summary['users_with_images']:
        print(f"User ID: {user['user_id']:3d} | Username: {user['username']:15s} | "
              f"Full Name: {user['full_name']:20s} | Ảnh: {user['image_count']:3d}")
    
    if summary['users_with_few_images']:
        print()
        print("USERS CÓ ÍT HƠN 5 ẢNH (SẼ BỊ BỎ QUA KHI TRAIN):")
        print("-" * 50)
        for user in summary['users_with_few_images']:
            print(f"User ID: {user['user_id']:3d} | Username: {user['username']:15s} | "
                  f"Full Name: {user['full_name']:20s} | Ảnh: {user['image_count']:3d}")

def validate_training_data():
    """Kiểm tra tính hợp lệ của dữ liệu training."""
    import sqlite3
    
    def get_db_connection():
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'database.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
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

def print_validation_result():
    """In ra kết quả validation dữ liệu."""
    result = validate_training_data()
    
    print("=" * 60)
    print("KIỂM TRA TÍNH HỢP LỆ CỦA DỮ LIỆU TRAINING")
    print("=" * 60)
    
    if result['is_valid']:
        print("✅ Dữ liệu hợp lệ!")
    else:
        print("❌ Dữ liệu có vấn đề:")
        for issue in result['issues']:
            print(f"  - {issue}")
    
    if result['warnings']:
        print("\n⚠️  Cảnh báo:")
        for warning in result['warnings']:
            print(f"  - {warning}")
    
    if result['missing_images']:
        print(f"\n📁 Ảnh không tồn tại ({len(result['missing_images'])}):")
        for img in result['missing_images'][:5]:  # Chỉ hiển thị 5 ảnh đầu
            print(f"  - {img}")
        if len(result['missing_images']) > 5:
            print(f"  ... và {len(result['missing_images']) - 5} ảnh khác")
    
    if result['duplicate_images']:
        print(f"\n🔄 Ảnh bị duplicate ({len(result['duplicate_images'])}):")
        for img in result['duplicate_images'][:5]:
            print(f"  - {img}")
        if len(result['duplicate_images']) > 5:
            print(f"  ... và {len(result['duplicate_images']) - 5} ảnh khác")

def print_user_mapping():
    """In ra mapping user_id -> full_name."""
    mapping = get_user_id_to_fullname_mapping()
    
    print("=" * 60)
    print("MAPPING USER_ID -> FULL_NAME")
    print("=" * 60)
    
    for user_id, full_name in mapping.items():
        print(f"User ID: {user_id:3s} -> {full_name}")

def export_training_data_info():
    """Export thông tin dữ liệu training ra file JSON để kiểm tra."""
    import sqlite3
    
    def get_db_connection():
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'database.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Lấy tất cả thông tin users và ảnh
    cur.execute("""
        SELECT u.user_id, u.username, u.full_name, fp.image_path
        FROM users u
        LEFT JOIN face_profiles fp ON u.user_id = fp.user_id
        ORDER BY u.user_id, fp.profile_id
    """)
    data = cur.fetchall()
    
    # Tổ chức dữ liệu theo user
    training_data = {}
    for row in data:
        user_id = str(row['user_id'])
        if user_id not in training_data:
            training_data[user_id] = {
                'user_id': row['user_id'],
                'username': row['username'],
                'full_name': row['full_name'],
                'images': []
            }
        if row['image_path']:
            training_data[user_id]['images'].append(row['image_path'])
    
    # Lọc bỏ users không có ảnh
    training_data = {k: v for k, v in training_data.items() if v['images']}
    
    # Thêm thông tin tổng quan
    summary = {
        'total_users_with_images': len(training_data),
        'total_images': sum(len(v['images']) for v in training_data.values()),
        'users_with_few_images': [k for k, v in training_data.items() if len(v['images']) < 5],
        'training_data': training_data
    }
    
    # Lưu ra file
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'training_data_info.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    conn.close()
    print(f"Đã export thông tin training data ra file: {json_path}")
    return summary

def check_database_status():
    """Kiểm tra trạng thái database và đồng bộ nếu cần."""
    print("🔍 KIỂM TRA TRẠNG THÁI DATABASE")
    print("=" * 50)
    
    # Kiểm tra file CSV
    csv_users = {}
    csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'users_export.csv')
    if os.path.exists(csv_path):
        import csv
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='|')
            for row in reader:
                if len(row) >= 3:
                    user_id, username, full_name = row[:3]
                    csv_users[username] = {
                        'user_id': int(user_id),
                        'username': username,
                        'full_name': full_name
                    }
    
    print(f"CSV users: {len(csv_users)}")
    
    # Kiểm tra database
    import sqlite3
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'database.db')
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    db_user_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM face_profiles")
    db_image_count = cur.fetchone()[0]
    conn.close()
    
    print(f"Database users: {db_user_count}")
    print(f"Database images: {db_image_count}")
    
    # Kiểm tra thư mục ảnh
    image_folders = []
    images_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'images_attendance')
    if os.path.exists(images_path):
        for folder in os.listdir(images_path):
            if folder.startswith('user_'):
                user_id = folder.split('_')[1]
                folder_path = os.path.join(images_path, folder)
                image_count = len([f for f in os.listdir(folder_path) 
                                 if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
                image_folders.append((user_id, image_count))
    
    print(f"Thư mục ảnh: {len(image_folders)} folders")
    
    # Đề xuất hành động
    if db_user_count == 0 and len(csv_users) > 0:
        print("\n⚠️  Database trống nhưng có dữ liệu CSV. Chạy sync_users_from_csv()")
    elif db_user_count != len(csv_users):
        print(f"\n⚠️  Số lượng users không khớp: CSV={len(csv_users)}, DB={db_user_count}")
    else:
        print("\n✅ Database và CSV đồng bộ")

def detect_mapping_errors():
    """Phát hiện lỗi mapping trong database."""
    print("\n🔍 PHÁT HIỆN LỖI MAPPING")
    print("=" * 50)
    
    import sqlite3
    
    def get_db_connection():
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'database.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    errors = []
    warnings = []
    
    # 1. Kiểm tra users không có full_name
    cur.execute("SELECT user_id, username FROM users WHERE full_name IS NULL OR full_name = ''")
    users_without_name = cur.fetchall()
    if users_without_name:
        errors.append({
            'type': 'missing_full_name',
            'count': len(users_without_name),
            'users': [{'user_id': u['user_id'], 'username': u['username']} for u in users_without_name]
        })
    
    # 2. Kiểm tra users có full_name trùng nhau
    cur.execute("SELECT full_name, COUNT(*) as count FROM users WHERE full_name IS NOT NULL GROUP BY full_name HAVING count > 1")
    duplicate_names = cur.fetchall()
    if duplicate_names:
        errors.append({
            'type': 'duplicate_full_name',
            'count': len(duplicate_names),
            'names': [{'name': d['full_name'], 'count': d['count']} for d in duplicate_names]
        })
    
    # 3. Kiểm tra mapping user_id -> full_name có hợp lý không
    cur.execute("""
        SELECT u.user_id, u.username, u.full_name, COUNT(fp.profile_id) as image_count
        FROM users u
        LEFT JOIN face_profiles fp ON u.user_id = fp.user_id
        GROUP BY u.user_id
        ORDER BY u.user_id
    """)
    users_with_images = cur.fetchall()
    
    suspicious_mappings = []
    for user in users_with_images:
        user_id = user['user_id']
        username = user['username']
        full_name = user['full_name']
        image_count = user['image_count']
        
        # Kiểm tra username và full_name có liên quan không
        if full_name and username:
            username_clean = username.lower().replace('_', ' ').replace('-', ' ')
            full_name_clean = full_name.lower().replace('_', ' ').replace('-', ' ')
            
            # Bỏ qua trường hợp username và full_name giống nhau
            if username_clean == full_name_clean:
                continue
                
            # Bỏ qua trường hợp username là một phần của full_name
            if username_clean in full_name_clean or full_name_clean in username_clean:
                continue
            
            # Chỉ báo lỗi khi thực sự nghi ngờ
            if len(full_name_clean) > 5 and len(username_clean) > 3:
                suspicious_mappings.append({
                    'user_id': user_id,
                    'username': username,
                    'full_name': full_name,
                    'image_count': image_count,
                    'reason': 'Username và full_name có thể không liên quan'
                })
    
    if suspicious_mappings:
        warnings.append({
            'type': 'suspicious_mapping',
            'count': len(suspicious_mappings),
            'mappings': suspicious_mappings
        })
    
    # 4. Kiểm tra file user_id_to_fullname.json nếu có
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'user_id_to_fullname.json')
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            training_mapping = json.load(f)
        
        # So sánh với database
        db_mapping = {}
        for user in users_with_images:
            if user['full_name'] and user['image_count'] > 0:  # CHỈ LẤY USER CÓ ẢNH
                db_mapping[str(user['user_id'])] = user['full_name']
        
        # Tìm mapping không khớp chỉ cho user có ảnh
        mismatches = []
        for user_id in db_mapping.keys():
            db_name = db_mapping.get(user_id)
            training_name = training_mapping.get(user_id)
            if db_name != training_name:
                mismatches.append({
                    'user_id': user_id,
                    'db_name': db_name,
                    'training_name': training_name
                })
        
        if mismatches:
            errors.append({
                'type': 'mapping_mismatch',
                'count': len(mismatches),
                'mismatches': mismatches
            })
    
    conn.close()
    
    return {
        'errors': errors,
        'warnings': warnings,
        'total_users': len(users_with_images),
        'users_with_images': len([u for u in users_with_images if u['image_count'] > 0])
    }

def print_mapping_errors(results):
    """In kết quả phát hiện lỗi mapping."""
    if results['errors']:
        print(f"\n❌ LỖI MAPPING PHÁT HIỆN:")
        for error in results['errors']:
            if error['type'] == 'missing_full_name':
                print(f"  - {error['count']} users không có full_name")
            elif error['type'] == 'duplicate_full_name':
                print(f"  - {error['count']} tên bị trùng")
            elif error['type'] == 'mapping_mismatch':
                print(f"  - {error['count']} mapping không khớp giữa DB và file training")
    
    if results['warnings']:
        print(f"\n⚠️  CẢNH BÁO MAPPING:")
        for warning in results['warnings']:
            if warning['type'] == 'suspicious_mapping':
                print(f"  - {warning['count']} mapping có thể sai")

def export_error_report(results):
    """Export báo cáo lỗi ra file chỉ khi có lỗi."""
    if not results['errors'] and not results['warnings']:
        print("\n✅ Không có lỗi mapping nào cần báo cáo")
        return
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'mapping_error_report_{timestamp}.json'
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 Đã export báo cáo lỗi ra file: {filename}")

def main():
    print("🔍 KIỂM TRA DỮ LIỆU TRAINING")
    print("=" * 60)
    
    # 1. Kiểm tra trạng thái database
    check_database_status()
    print()
    
    # 2. In tổng quan dữ liệu
    print_training_data_summary()
    print()
    
    # 3. Kiểm tra validation
    print_validation_result()
    print()
    
    # 4. In mapping user_id -> full_name
    print_user_mapping()
    print()
    
    # 5. Phát hiện lỗi mapping
    mapping_results = detect_mapping_errors()
    print_mapping_errors(mapping_results)
    
    # 6. Export thông tin chi tiết
    print("\n📊 Export thông tin chi tiết...")
    summary = export_training_data_info()
    
    # 7. Export báo cáo lỗi mapping (chỉ khi có lỗi)
    export_error_report(mapping_results)
    
    # 8. Tóm tắt
    print("\n" + "=" * 60)
    print("TÓM TẮT")
    print("=" * 60)
    
    validation = validate_training_data()
    mapping = get_user_id_to_fullname_mapping()
    
    print(f"✅ Users có ảnh: {summary['total_users_with_images']}")
    print(f"📸 Tổng số ảnh: {summary['total_images']}")
    print(f"⚠️  Users có ít hơn 5 ảnh: {len(summary['users_with_few_images'])}")
    print(f"🔍 Vấn đề phát hiện: {len(validation['issues'])}")
    print(f"⚠️  Cảnh báo: {len(validation['warnings'])}")
    print(f"🔍 Lỗi mapping: {len(mapping_results['errors'])}")
    print(f"⚠️  Cảnh báo mapping: {len(mapping_results['warnings'])}")
    
    if validation['is_valid'] and len(mapping_results['errors']) == 0:
        print("\n🎉 Dữ liệu sẵn sàng để train!")
        print("Bạn có thể chạy: python finish_train.py")
    else:
        print("\n❌ Cần sửa lỗi trước khi train!")
        print("Vui lòng chạy: python fix_database.py để sửa lỗi")
        print("Sau đó chạy lại: python check_training_data.py")

if __name__ == "__main__":
    main() 