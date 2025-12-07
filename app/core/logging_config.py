"""Logging configuration for the application."""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Create logs directory if it doesn't exist
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Configure logging format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Create formatter
formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

# Root logger configuration
logger = logging.getLogger("app")
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# File handler with rotation (10MB max, keep 5 backups)
file_handler = RotatingFileHandler(
    LOG_DIR / "app.log",
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

# Error file handler (only errors and above)
error_handler = RotatingFileHandler(
    LOG_DIR / "errors.log",
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5
)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)
logger.addHandler(error_handler)

# Prevent duplicate logs from uvicorn
logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

