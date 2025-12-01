from ultralytics import YOLO
import os

if __name__ == '__main__':
    # # Load the model.
    model = YOLO('yolov8x.pt')

    # Training.
    results = model.train(
        data='body_landmarks.yml',
        imgsz=640,
        epochs=25,
        batch=16,
        name='orchestrate',
        device=2
    )
