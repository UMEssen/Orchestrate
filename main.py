import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from utils.config import LOG_DIR, ensure_runtime_directories, missing_checkpoints

# Ensure logs directory exists
ensure_runtime_directories()

# Configure logging
log_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
log_file = LOG_DIR / "api.log"

handler = RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=3)
handler.setFormatter(log_formatter)
handler.setLevel(logging.INFO)

logger = logging.getLogger("api_logger")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# FastAPI
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from enum import Enum

# Orchestrate
from models.orchestrator import orchestrate_models, orchestrate_all_study


app = FastAPI(
    title="Orchestrate",
    description="Automated CT series labeling using a collection of deep learning models.",
)

class FileType(str, Enum):
    dcm = "dcm"

class FilePathInput(BaseModel):
    path: str
    file_type: FileType

    
def validate_request(file: FilePathInput) -> None:
    if file.file_type != FileType.dcm:
        raise HTTPException(status_code=400, detail="Only DICOM input (file_type='dcm') is currently supported.")
    if not Path(file.path).is_dir():
        raise HTTPException(status_code=400, detail=f"Input directory does not exist: {file.path}")
    missing = missing_checkpoints()
    if missing:
        raise HTTPException(
            status_code=503,
            detail={"message": "Required model checkpoints are missing.", "missing_checkpoints": missing},
        )


@app.post("/orchestrate")
def orchestrator_endpoint(file: FilePathInput):
    logger.info(f"Received request at Orchestrate")
    validate_request(file)
    try:
        result = orchestrate_models(file.path)
        logger.info(f"orchestrate models result: {result}")
        return result
    except Exception as e:
        logger.exception("Error in orchestrate_models")
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.post("/orchestrate_all")
def orchestrator_all_endpoint(file: FilePathInput):
    logger.info(f"Received request at Orchestrate")
    validate_request(file)
    try:
        result = orchestrate_all_study(file.path)
        logger.info(f"orchestrate models result: {result}")
        return result
    except Exception as e:
        logger.exception("Error in orchestrate_models")
        raise HTTPException(status_code=500, detail=str(e)) from e
