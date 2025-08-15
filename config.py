#!/usr/bin/env python3
"""
File cấu hình chung cho hệ thống
"""

import os

# Đường dẫn gốc của dự án
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Đường dẫn database
DATABASE_PATH = os.path.join(PROJECT_ROOT, "database", "database.db")

# Đường dẫn thư mục ảnh
IMAGES_PATH = os.path.join(PROJECT_ROOT, "images_attendance")

# Đường dẫn models
MODELS_PATH = os.path.join(PROJECT_ROOT, "models")

# Đường dẫn training
TRAINING_PATH = os.path.join(PROJECT_ROOT, "training")

def get_database_path():
    """Lấy đường dẫn database"""
    return DATABASE_PATH

def get_images_path():
    """Lấy đường dẫn thư mục ảnh"""
    return IMAGES_PATH

def get_models_path():
    """Lấy đường dẫn models"""
    return MODELS_PATH

def get_training_path():
    """Lấy đường dẫn training"""
    return TRAINING_PATH
