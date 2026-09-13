from utils.helper import yolo_detector
from utils.preprocessing import foreign_meta_preprocessing

def FremdmetallDetector(data_path: str) -> dict:
    data = foreign_meta_preprocessing(data_path)
    model_path = "checkpoints/fremdmetall.pt"
    result = yolo_detector(data, model_path)
    return result

