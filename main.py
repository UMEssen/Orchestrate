import logging
from logging.handlers import RotatingFileHandler
import os

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

# FastAPI
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from enum import Enum

# Orchestrate
from models.orchestrator import orchestrate_models, orchestrate_all_study


app = FastAPI()
class FileType(str, Enum):
    png = "png"
    nii = "nii"
    dcm = "dcm"

class FilePathInput(BaseModel):
    path: str
    file_type: FileType

    
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