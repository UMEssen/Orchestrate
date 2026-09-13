from ultralytics import YOLO
import torch
import cv2
import numpy as np
def letterbox(img, target_size=(640, 640), color=(114, 114, 114)):
    """
    Automatically scale image 
    Returns shape (target_h, target_w, 3)
    """

    original_h, original_w = img.shape[:2]
    target_w, target_h = target_size

    scale = min(target_w / original_w, target_h / original_h)

    new_w = int(round(original_w * scale))
    new_h = int(round(original_h * scale))

    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    img_padded = np.full((target_h, target_w, 3), color, dtype=resized.dtype)

    top = (target_h - new_h) // 2
    left = (target_w - new_w) // 2

    img_padded[top:top+new_h, left:left+new_w] = resized

    return img_padded

def top_bbox_per_class(bboxes, scores, classes):
    unique_classes = classes.unique()
    
    top_boxes = []
    top_scores = []
    top_classes = []
    
    for cls in unique_classes:
        mask = classes == cls
        cls_scores = scores[mask]
        cls_bboxes = bboxes[mask]
        
        best_idx = torch.argmax(cls_scores)
        top_boxes.append(cls_bboxes[best_idx])
        top_scores.append(cls_scores[best_idx])
        top_classes.append(cls)
    
    return torch.stack(top_boxes), torch.stack(top_scores), torch.stack(top_classes)

def yolo_detector(data: str, model_path:str)-> dict:
    model = YOLO(model_path)
    result_bbox = []
    result_cls = []
    result_scores = []

    if data.shape[1] == 640:
        data_resized = data
    else:
        data_resized = letterbox(data)

    if data_resized.max() > 1.0:
        data_resized = data_resized / 255.0

    data_tensor = torch.from_numpy(data_resized).permute(2, 0, 1).unsqueeze(0).to('cuda')

    results = model(data_tensor, device=5)
    
    for result in results:
        boxes = result.boxes  
        result_cls.append(boxes.cls)
        result_bbox.append(boxes.xyxy)
        result_scores.append(boxes.conf)

    if len(result_cls[0]) == 0:

        return "no detections"
    else:
        best_bboxes, best_scores, best_classes = top_bbox_per_class(result_bbox[0], result_scores[0],result_cls[0])
        predicted = { 
                "bounding_box": best_bboxes, 
                "class":best_classes,
                "scores": best_scores}
    
        return predicted

def yolo_classifier(data: str, model_path:str)-> dict:
    if data.shape[1] == 640:
        data_resized = data
    else:
        data_resized = letterbox(data)

    if data_resized.max() > 1.0:
        data_resized = data_resized / 255.0

    data_tensor = torch.from_numpy(data_resized).permute(2, 0, 1).unsqueeze(0).to('cuda')

    model = YOLO(model_path)
    result = model(data_tensor)  
    probs_list = [item.probs for item in result]
    probs = [probs.data.cpu().numpy().tolist() for probs in probs_list][0]
    max_prob = max(probs)

    prob_idx = probs.index(max_prob)
    predicted = result[0].names[prob_idx]

    return {"result":predicted}

