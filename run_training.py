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
        print("\n🔍 Kiểm tra nhanh dữ liệu trước khi train...")
        
        # Tự động đồng bộ DB với folder trước khi train
        try:
            from training.check_training_data import sync_images_from_folders
            print("🔄 Đang đồng bộ database với folder ảnh...")
            sync_results = sync_images_from_folders()
            
            if sync_results:
                print(f"✅ Đã đồng bộ: {sync_results['total_images_found']} ảnh")
                if sync_results['deleted_from_db'] > 0 or sync_results['added_to_db'] > 0:
                    print(f"   - Xóa: {sync_results['deleted_from_db']}, Thêm: {sync_results['added_to_db']}")
            else:
                print("⚠️  Không thể đồng bộ database")
                
        except Exception as e:
            print(f"⚠️  Lỗi khi đồng bộ database: {e}")
            print("Tiếp tục train với dữ liệu hiện tại...")
        
        # Kiểm tra nhanh dữ liệu
        try:
            from database.db import get_training_data_summary
            summary = get_training_data_summary()
            
            if summary['total_images'] == 0:
                print("❌ Không có ảnh nào để train!")
                print("Vui lòng thêm ảnh trước khi train.")
                print("Tiếp tục train với dữ liệu hiện tại...")
            
            if summary['users_with_few_images']:
                print("⚠️  Cảnh báo: Có users có ít hơn 5 ảnh")
                for user in summary['users_with_few_images']:
                    print(f"  - {user['username']}: {user['image_count']} ảnh")
                print("Các users này sẽ bị bỏ qua khi train.")
            
            print(f"\n📊 Tổng quan dữ liệu:")
            print(f"   - Users có ảnh: {summary['total_users']}")
            print(f"   - Tổng số ảnh: {summary['total_images']}")
            
        except Exception as e:
            print(f"⚠️  Không thể kiểm tra dữ liệu: {e}")
        
        print("\n🚀 Bắt đầu train...")
        train_model()
    elif choice == '3':
        print("Tạm biệt!")
    else:
        print("Lựa chọn không hợp lệ") 