import os
import cv2
cv2.setNumThreads(1)  # Giới hạn OpenCV chỉ dùng 1 luồng
import numpy as np
import logging
import h5py
import pickle
import gc
from deepface import DeepFace
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from concurrent.futures import ThreadPoolExecutor
from facenet_pytorch import MTCNN
from PIL import Image
import sqlite3
import json
import sys
import os
# Thêm thư mục cha vào path để import các module khác
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import get_training_data_summary
import sys
import time

def clear_log_file():
    """Xóa nội dung file training.log."""
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'training.log')
    with open(log_path, 'w') as f:
        f.write('')
    logging.info("Đã xóa nội dung file training.log")

# Thiết lập logging
log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'training.log')
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def ensure_directories():
    """Tạo các thư mục cần thiết."""
    os.makedirs('processed_faces', exist_ok=True)
    os.makedirs('models', exist_ok=True)
    logging.info("Đã tạo các thư mục cần thiết")

def clear_processed_faces():
    """Xóa thư mục processed_faces."""
    import shutil
    if os.path.exists('processed_faces'):
        shutil.rmtree('processed_faces')
    os.makedirs('processed_faces')
    logging.info("Đã xóa và tạo lại thư mục processed_faces")

def smart_extract_and_save_faces_from_db(target_size=(160, 160)):
    """
    Trích xuất khuôn mặt từ ảnh và lưu vào processed_faces một cách thông minh.
    Chỉ xử lý lại ảnh đã thay đổi hoặc chưa được xử lý.
    """
    mtcnn = MTCNN(
        image_size=target_size[0],
        margin=30,
        min_face_size=50,
        thresholds=[0.7, 0.8, 0.9],
        device='cpu'
    )
    
    processed_faces_dir = 'processed_faces'
    os.makedirs(processed_faces_dir, exist_ok=True)
    
    # Lấy danh sách ảnh từ DB
    conn = sqlite3.connect(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'database.db'))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute('''
        SELECT users.user_id, users.full_name, face_profiles.image_path
        FROM face_profiles
        JOIN users ON face_profiles.user_id = users.user_id
    ''')
    data = cur.fetchall()
    conn.close()
    
    total_images = len(data)
    total_processed = 0
    total_skipped = 0
    total_failed = 0
    user_id_to_fullname = {}
    
    logging.info(f"Bắt đầu xử lý {total_images} ảnh...")
    
    for idx, row in enumerate(data, 1):
        user_id = row['user_id']
        full_name = row['full_name']
        user_id_to_fullname[str(user_id)] = full_name
        image_path = row['image_path']
        
        # Tạo đường dẫn output
        output_person_dir = os.path.join(processed_faces_dir, str(user_id))
        os.makedirs(output_person_dir, exist_ok=True)
        output_filename = f"processed_{os.path.basename(image_path)}"
        output_path = os.path.join(output_person_dir, output_filename)
        
        # Kiểm tra xem ảnh đã được xử lý chưa và có cần xử lý lại không
        need_process = True
        if os.path.exists(output_path):
            # So sánh thời gian sửa đổi
            original_mtime = os.path.getmtime(image_path)
            processed_mtime = os.path.getmtime(output_path)
            
            if processed_mtime >= original_mtime:
                # Ảnh đã được xử lý và không thay đổi
                need_process = False
                total_skipped += 1
        
        if need_process:
            try:
                img = Image.open(image_path).convert('RGB')
                face = mtcnn(img)
                if face is not None:
                    face = face.permute(1, 2, 0).numpy()
                    face = (face - face.min()) / (face.max() - face.min() + 1e-8)
                    face = (face * 255.0).astype(np.uint8)
                    face_pil = Image.fromarray(face)
                    face_pil.save(output_path)
                    total_processed += 1
                else:
                    logging.warning(f"Không phát hiện được khuôn mặt trong ảnh: {image_path}")
                    total_failed += 1
            except Exception as e:
                logging.error(f"Lỗi xử lý ảnh {image_path}: {e}")
                total_failed += 1
                continue
        
        # Cập nhật tiến độ
        if idx % 20 == 0 or idx == total_images:
            percent = round((idx / total_images) * 50) if total_images else 0
            logging.info(f"Tiến trình: {idx}/{total_images} ({percent}%)")
            print(f"Tiến trình: {idx}/{total_images} ({percent}%)", flush=True)
        time.sleep(0.05)  # Giảm tải CPU
    
    logging.info(f"Hoàn thành xử lý ảnh:")
    logging.info(f"- Ảnh mới xử lý: {total_processed}")
    logging.info(f"- Ảnh đã có (bỏ qua): {total_skipped}")
    logging.info(f"- Ảnh thất bại: {total_failed}")
    logging.info(f"Tiến trình: (50%)")
    print(f"Tiến trình: Hoàn thành xử lý ảnh (50%)", flush=True)
    
    # Lưu ánh xạ ra file
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'user_id_to_fullname.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(user_id_to_fullname, f, ensure_ascii=False)
    
    return processed_faces_dir

def process_batch(batch, embedding_model='Facenet512'):
    """Xử lý batch ảnh với FaceNet-512d."""
    batch_embeddings = []
    
    try:
        for img in batch:
            embedding_result = DeepFace.represent(
                img,
                model_name=embedding_model,
                enforce_detection=False,
                detector_backend='skip',
                align=False,
                normalization='base',
                anti_spoofing=False
            )[0]
            
            embedding = embedding_result['embedding']
            batch_embeddings.append(embedding)
            
    except Exception as e:
        logging.error(f"Lỗi xử lý batch: {str(e)}")
        return []
        
    return batch_embeddings

def create_training_data(
    processed_faces_dir,
    output_train_file=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models', 'train_FN.h5'),
    embedding_model='Facenet512',
    batch_size=2,  # Giảm batch_size để giảm tải CPU
    test_size=0.2,
    random_state=42,
    target_size=(160, 160)
):
    """
    Tạo dữ liệu train từ ảnh khuôn mặt đã được cắt.
    Args:
        embedding_model: 'Facenet' (128 chiều) hoặc 'Facenet512' (512 chiều)
        batch_size: Kích thước batch, đề xuất 4 cho Raspberry Pi 5
    """
    os.makedirs(os.path.dirname(output_train_file), exist_ok=True)
    
    embeddings = []
    labels = []
    failed_images = []
    
    if embedding_model not in ['Facenet', 'Facenet512']:
        raise ValueError("embedding_model phải là 'Facenet' hoặc 'Facenet512'")
    
    try:
        person_dirs = [d for d in os.listdir(processed_faces_dir)
                      if os.path.isdir(os.path.join(processed_faces_dir, d))]
        
        if not person_dirs:
            raise ValueError("Không tìm thấy thư mục người nào")
            
        logging.info(f"Tìm thấy {len(person_dirs)} thư mục người")
        
        json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'user_id_to_fullname.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            user_id_to_fullname = json.load(f)
        
        total_embedding_images = 0
        for person_name in person_dirs:
            person_path = os.path.join(processed_faces_dir, person_name)
            logging.info(f"Đang xử lý thư mục: {person_name}")
            image_files = [
                f for f in os.listdir(person_path)
                if f.startswith(('processed_', 'augmented_'))
            ]
            if len(image_files) < 5:
                logging.warning(f"Thư mục {person_name} có ít hơn 5 ảnh, bỏ qua")
                continue
            total_embedding_images += len(image_files)
        # Reset lại biến đếm
        embedding_processed = 0
        
        for person_name in person_dirs:
            person_path = os.path.join(processed_faces_dir, person_name)
            logging.info(f"Đang xử lý thư mục: {person_name}")
            image_files = [
                f for f in os.listdir(person_path)
                if f.startswith(('processed_', 'augmented_'))
            ]
            if len(image_files) < 5:
                continue
            batches = [image_files[i:i + batch_size] for i in range(0, len(image_files), batch_size)]
            for batch in batches:
                batch_images = []
                batch_paths = []
                for image_file in batch:
                    image_path = os.path.join(person_path, image_file)
                    try:
                        img = cv2.imread(image_path)
                        if img is None:
                            failed_images.append((image_file, "Không thể đọc ảnh"))
                            continue
                        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                        img = img.astype(np.float32) / 255.0
                        batch_images.append(img)
                        batch_paths.append(image_file)
                    except Exception as e:
                        failed_images.append((image_file, str(e)))
                        continue
                if batch_images:
                    with ThreadPoolExecutor(max_workers=1) as executor:  # Giảm tải hệ thống tối đa
                        batch_embeddings = executor.submit(process_batch, batch_images, embedding_model).result()
                    for embedding, image_file in zip(batch_embeddings, batch_paths):
                        if embedding:
                            embeddings.append(embedding)
                            label = user_id_to_fullname.get(person_name, person_name)
                            labels.append(label)
                        else:
                            failed_images.append((image_file, "Lỗi tạo embedding"))
                        embedding_processed += 1
                        # Cập nhật tiến độ sau mỗi 20 ảnh embedding, chia đều từ 50% đến 100%
                        if embedding_processed % 20 == 0 or embedding_processed == total_embedding_images:
                            percent = 50 + round((embedding_processed / total_embedding_images) * 50) if total_embedding_images else 50
                            logging.info(f"Tiến trình: {embedding_processed}/{total_embedding_images} ({percent}%)")
                            print(f"Tiến trình: {embedding_processed}/{total_embedding_images} ({percent}%)", flush=True)
                    del batch_images
                    gc.collect()
                time.sleep(0.05)  # Giảm tải CPU
        
        # Sau khi trích xuất embedding xong, log 90%
        logging.info(f"Tiến trình: (90%)")
        print(f"Tiến trình: Hoàn thành trích xuất embedding (90%)", flush=True)
        if embeddings:
            label_encoder = LabelEncoder()
            encoded_labels = label_encoder.fit_transform(labels)
            
            X_train, X_val, y_train, y_val = train_test_split(
                np.array(embeddings),
                encoded_labels,
                test_size=test_size,
                random_state=random_state,
                stratify=encoded_labels
            )
            
            X_train = X_train / np.linalg.norm(X_train, axis=1, keepdims=True)
            X_val = X_val / np.linalg.norm(X_val, axis=1, keepdims=True)
            
            with h5py.File(output_train_file, 'w') as f:
                f.create_dataset('embeddings', data=X_train)
                f.create_dataset('labels', data=y_train)
                f.create_dataset('X_val', data=X_val)
                f.create_dataset('y_val', data=y_val)
                f.attrs['embedding_model'] = embedding_model
                f.attrs['embedding_size'] = 512 if embedding_model == 'Facenet512' else 128
                
            with open(output_train_file.replace('.h5', '_label_encoder.pkl'), 'wb') as f_le:
                pickle.dump(label_encoder, f_le)
            
            logging.info(f"Đã tạo file train tại: {output_train_file}")
            logging.info(f"Số lượng ảnh train: {len(y_train)}")
            logging.info(f"Số lượng ảnh validation: {len(y_val)}")
            
            if failed_images:
                logging.warning(f"Tổng số ảnh lỗi: {len(failed_images)}")
                log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'failed_images.log')
                with open(log_path, 'w', encoding='utf-8') as f:
                    for img, reason in failed_images:
                        f.write(f"{img}: {reason}\n")
            # Đảm bảo in ra đúng 100% khi kết thúc
            logging.info(f"Tiến trình: (100%)")
            print(f"Tiến trình: Hoàn thành tạo file train (100%)", flush=True)
        else:
            raise ValueError("Không có dữ liệu khuôn mặt nào được xử lý.")
            
    except Exception as e:
        logging.error(f"Lỗi tạo dữ liệu train: {str(e)}")
        raise

def main():
    try:
        start_time = time.time()
        # Giảm ưu tiên CPU cho tiến trình train
        try:
            os.nice(10)
        except Exception:
            pass
        # Kiểm tra argument dòng lệnh
        mode = None
        if len(sys.argv) > 1:
            if '--smart' in sys.argv:
                mode = '1'
            elif '--all' in sys.argv:
                mode = '2'
        # Kiểm tra dữ liệu trước khi train
        print("🔍 Kiểm tra dữ liệu training...")
        
        # Import từ check_training_data để tránh trùng lặp
        from training.check_training_data import detect_mapping_errors
        
        # Kiểm tra cơ bản
        summary = get_training_data_summary()
        if summary['total_users'] == 0:
            print("❌ Không có users nào trong database!")
            print("Vui lòng thêm users trước khi train.")
            return
        
        if summary['total_images'] == 0:
            print("❌ Không c1ó ảnh nào trong database!")
            print("Vui lòng thêm ảnh trước khi train.")
            return
        
        # Kiểm tra users có ít ảnh
        if summary['users_with_few_images']:
            print("⚠️  Cảnh báo: Có users có ít hơn 5 ảnh:")
            for user in summary['users_with_few_images']:
                print(f"  - {user['username']} ({user['image_count']} ảnh)")
            print("Các users này sẽ bị bỏ qua khi train.")
        
        # Kiểm tra mapping errors
        mapping_results = detect_mapping_errors()
        if mapping_results['errors']:
            print("❌ Phát hiện lỗi mapping:")
            for error in mapping_results['errors']:
                print(f"  - {error['type']}: {error['count']} lỗi")
            print("Vui lòng chạy: python fix_database.py để sửa lỗi")
            return
        
        print("✅ Dữ liệu hợp lệ, bắt đầu train...")
        print(f"📊 Tổng users: {summary['total_users']}, Tổng ảnh: {summary['total_images']}")
        
        # Hỏi người dùng về cách xử lý ảnh
        if mode is None:
            print("\n🔄 CHỌN CÁCH XỬ LÝ ẢNH:")
            print("1. Thông minh (chỉ xử lý ảnh đã thay đổi) - Khuyến nghị")
            print("2. Xử lý lại tất cả ảnh")
            while True:
                choice = input("Chọn (1/2): ").strip()
                if choice in ['1', '2']:
                    break
                print("Vui lòng chọn 1 hoặc 2")
        else:
            choice = mode
        clear_log_file()  # Xóa log cũ trước khi bắt đầu
        ensure_directories()
        
        if choice == '1':
            # Xử lý thông minh
            print("🚀 Sử dụng xử lý thông minh...")
            processed_faces_dir = smart_extract_and_save_faces_from_db(target_size=(160, 160))
        else:
            # Xử lý lại tất cả
            print("🔄 Xử lý lại tất cả ảnh...")
            clear_processed_faces()
            processed_faces_dir = smart_extract_and_save_faces_from_db(target_size=(160, 160))
        create_training_data(
            processed_faces_dir=processed_faces_dir,
            output_train_file=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "train_FN.h5"),
            embedding_model='Facenet512',
            batch_size=2,
            test_size=0.2
        )
        
    except Exception as e:
        logging.error(f"Lỗi trong quá trình train: {str(e)}")
        raise
    # Sau khi hoàn thành train (sau khi in tiến trình 100%)
    end_time = time.time()
    elapsed = int(end_time - start_time)
    minutes = elapsed // 60
    seconds = elapsed % 60
    elapsed_str = f"{minutes} phút {seconds} giây"
    logging.info(f"Thời gian huấn luyện: {elapsed_str}")
    print(f"⏱️ Thời gian huấn luyện: {elapsed_str}", flush=True)

if __name__ == "__main__":
    main()