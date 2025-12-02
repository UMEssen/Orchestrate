from utils.helper import yolo_detector,yolo_classifier

def BodyPartPredictor(data):
    model_path = "checkpoints/rapid_bodypart.pt"    
    result = yolo_classifier(data, model_path)
    return result

def BodyRegionDetector(data):
    model_path = "checkpoints/rapid_region.pt"
    result = yolo_detector(data, model_path)
    return result

def BodyOrganDetector(data):
    model_path = "checkpoints/rapid_organ.pt"
    result = yolo_detector(data, model_path)
    return result

def LateralBrainDetector(data):
    model_path = "checkpoints/lateral_rapid_brain.pt"
    result = yolo_detector(data, model_path)
    return result