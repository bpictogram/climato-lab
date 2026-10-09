import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# print(f"Path(__file__): {Path(__file__).resolve()}")
# print(f"PROJECT_ROOT: {PROJECT_ROOT}")


def get_dump_dir() -> Path:
    configured_path = os.getenv("CLIMATO_DUMP_DIR")

    if configured_path:
        return Path(configured_path).expanduser().resolve()

    return PROJECT_ROOT / "dump"


def get_raw_data_dir() -> Path:
    configured_path = os.getenv("CLIMATO_RAW_DATA_DIR")
    
    if configured_path:
        raw_data_dir = Path(configured_path).expanduser().resolve()
    else:
        raw_data_dir = PROJECT_ROOT / "data" / "raw"
    
    return raw_data_dir


def get_daily_data_dir() -> Path:
    return (get_raw_data_dir() / "meteo_france" / "daily").resolve()
