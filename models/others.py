from utils.helper import yolo_detector
from utils.preprocessing import foreign_meta_preprocessing
from utils.config import checkpoint_path

def FremdmetallDetector(data_path: str) -> dict:
    data = foreign_meta_preprocessing(data_path)
    model_path = checkpoint_path("fremdmetall.pt")
    result = yolo_detector(data, model_path)
    return result
