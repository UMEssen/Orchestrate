from utils.helper import yolo_classifier
from utils.preprocessing import contrast_preprocessing,braincontrast_preprocessing

def ContrastClassifier(data_path: str) -> dict:
    data = contrast_preprocessing(data_path)
    model_path = "checkpoints/contrast.pt"
    result = yolo_classifier(data, model_path)
    return result


def BrainContrastClassifier(data_path: str) -> dict:
    data = braincontrast_preprocessing(data_path)
    model_path = "checkpoints/brain_contrast.pt"
    result = yolo_classifier(data, model_path)
    return result

