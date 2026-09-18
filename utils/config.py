"""Shared runtime paths and checkpoint configuration."""

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_DIR = PROJECT_ROOT / "db"
CHECKPOINT_DIR = Path(os.getenv("ORCHESTRATE_CHECKPOINT_DIR", PROJECT_ROOT / "checkpoints"))
LOG_DIR = Path(os.getenv("ORCHESTRATE_LOG_DIR", PROJECT_ROOT / "logs"))
OUTPUT_DB = Path(os.getenv("ORCHESTRATE_OUTPUT_DB", DB_DIR / "orchestrait.db"))
METADATA_DB = Path(os.getenv("ORCHESTRATE_METADATA_DB", DB_DIR / "metadata.db"))

REQUIRED_CHECKPOINTS = (
    "viewposition.pt",
    "rapid_bodypart.pt",
    "rapid_region.pt",
    "rapid_organ.pt",
    "lateral_rapid_brain.pt",
    "kernel_new.pt",
    "contrast.pt",
    "brain_contrast.pt",
    "fremdmetall.pt",
)


def checkpoint_path(filename: str) -> str:
    return str(CHECKPOINT_DIR / filename)


def missing_checkpoints() -> list[str]:
    return [name for name in REQUIRED_CHECKPOINTS if not (CHECKPOINT_DIR / name).is_file()]


def ensure_runtime_directories() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DB.parent.mkdir(parents=True, exist_ok=True)
    METADATA_DB.parent.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
