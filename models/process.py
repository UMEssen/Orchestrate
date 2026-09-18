from utils.helper import yolo_classifier
from utils.preprocessing import kernel_preprocessing
from utils.config import checkpoint_path

def KernelClassifier(data_path: str) -> dict:
    data = kernel_preprocessing(data_path)
    model_path = checkpoint_path("kernel_new.pt")
    result = yolo_classifier(data, model_path)
    return result
    
def ViewPositionClassifier(topo_data):
    model_path = checkpoint_path("viewposition.pt")
    result = yolo_classifier(topo_data, model_path)
    return result
