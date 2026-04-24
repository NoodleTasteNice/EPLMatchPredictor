# src/utils/logger.py
import logging
import os
from pathlib import Path

def get_logger(name):
    logger = logging.getLogger(name)
    
    # avoid duplicates
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)
    
    # ensure logs directory exists
    root_dir = Path(__file__).resolve().parent.parent.parent
    log_dir = root_dir / "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # write to logs/pipeline.log
    file_handler = logging.FileHandler(log_dir / "pipeline.log")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(
        '{"time": "%(asctime)s", "level": "%(levelname)s", "module": "%(name)s", "message": "%(message)s"}'
    ))
    
    # print to terminal
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
    ))
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger