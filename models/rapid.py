from utils.helper import yolo_detector,yolo_classifier
from utils.config import checkpoint_path

def BodyPartPredictor(data):
    model_path = checkpoint_path("rapid_bodypart.pt")
    result = yolo_classifier(data, model_path)
    return result

def BodyRegionDetector(data):
    model_path = checkpoint_path("rapid_region.pt")
    result = yolo_detector(data, model_path)
    return result

def BodyOrganDetector(data):
    model_path = checkpoint_path("rapid_organ.pt")
    result = yolo_detector(data, model_path)
    return result

def LateralBrainDetector(data):
    model_path = checkpoint_path("lateral_rapid_brain.pt")
    result = yolo_detector(data, model_path)
    return result
