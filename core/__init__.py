# Core Package - Chứa các module cốt lõi của hệ thống
from .recognition_class import RecognitionSystem
from .recognition_simple import RecognitionSimple
from .smart_tts import play_name_smart
from .pir_sensor import PIRSensor

__all__ = [
    'RecognitionSystem',
    'RecognitionSimple', 
    'play_name_smart',
    'PIRSensor'
] 