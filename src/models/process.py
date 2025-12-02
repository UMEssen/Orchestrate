from utils.helper import yolo_classifier
from utils.preprocessing import kernel_preprocessing

def KernelClassifier(data_path: str) -> dict:
    data = kernel_preprocessing(data_path)
    model_path = "checkpoints/kernel_new.pt"
    result = yolo_classifier(data, model_path)
    return result
    
def ViewPositionClassifier(topo_data):
    model_path = "checkpoints/viewposition.pt"
    result = yolo_classifier(topo_data, model_path)
    return result
