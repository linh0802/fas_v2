# GUI Modules Package
# Chứa tất cả các module GUI đã được tách riêng

from .gui_main import AttendanceGUI
from .gui_config import *
from .gui_components import EnlargedFaceWindow, OnScreenKeyboardFrame
from .gui_frames import AttendanceDataFrame
from .recognition_frame import RecognitionFrame
from .data_entry_frame import DataEntryFrame

__all__ = [
    'AttendanceGUI',
    'EnlargedFaceWindow',
    'OnScreenKeyboardFrame', 
    'AttendanceDataFrame',
    'RecognitionFrame',
    'DataEntryFrame'
] 