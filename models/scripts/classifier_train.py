from ultralytics import YOLO

model = YOLO('yolov8x-cls.pt')  
path = "data/train"
model.train(data=path,batch=16,epochs=25, imgsz=640, name='orchestrate', device=5)