import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def get_data_dir() -> Path:
    configured_path = os.getenv("CLIMATO_DATA_DIR")
    
    if configured_path:
        data_dir = Path(configured_path).expanduser().resolve()
    else:
        data_dir = PROJECT_ROOT / "data"
    
    return data_dir


def get_raw_data_dir() -> Path:
    configured_path = os.getenv("CLIMATO_RAW_DATA_DIR")
    
    if configured_path:
        raw_data_dir = Path(configured_path).expanduser().resolve()
    else:
        raw_data_dir = PROJECT_ROOT / "data" / "raw"
    
    return raw_data_dir


def get_daily_data_dir() -> Path:
    return (get_raw_data_dir() / "meteo_france" / "daily").resolve()
