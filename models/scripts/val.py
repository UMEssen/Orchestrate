from ultralytics import YOLO


model = YOLO('runs/detect/orchestrate/weights/best.pt')  


metrics = model.val(device=0)
print(f"MAP: {metrics.box.map}")    # map50-95
print(f"MAP50: {metrics.box.map50}")  # map50
print(f"MAP75: {metrics.box.map75}")  # map75
print(f"MAP individual: {metrics.box.maps}")   # a list contains map50-95 of each category

