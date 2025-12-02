import logging
from logging.handlers import RotatingFileHandler
import os
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel
from models.orchestrator import orchestrate_models, orchestrate_all_study
from ultralytics import YOLO

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Configure logging
log_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
log_file = "logs/api.log"

handler = RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=3)
handler.setFormatter(log_formatter)
handler.setLevel(logging.INFO)

logger = logging.getLogger("api_logger")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

app = FastAPI()
class FilePathInput(BaseModel):
    path: str
    
@app.post("/orchestrate")
async def orchestrator_endpoint(file: FilePathInput):
    logger.info(f"Received request at Orchestrate")
    try:
        result = orchestrate_models(file.path)
        logger.info(f"orchestrate models result: {result}")
        return result
    except Exception as e:
        logger.exception("Error in orchestrate_models")
        return {"error": str(e)}

@app.post("/orchestrate_all")
async def orchestrator_all_endpoint(file: FilePathInput):
    logger.info(f"Received request at Orchestrate")
    try:
        result = orchestrate_all_study(file.path)
        logger.info(f"orchestrate models result: {result}")
        return result
    except Exception as e:
        logger.exception("Error in orchestrate_models")
        return {"error": str(e)}