import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.expanduser("~/.lstock")
LOG_PATH = os.path.join(LOG_DIR, "app.log")


def get_logger() -> logging.Logger:
	if not os.path.isdir(LOG_DIR):
		os.makedirs(LOG_DIR, exist_ok=True)

	logger = logging.getLogger("lstock")
	if logger.handlers:
		return logger

	logger.setLevel(logging.INFO)

	file_handler = RotatingFileHandler(LOG_PATH, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
	file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
	logger.addHandler(file_handler)

	console_handler = logging.StreamHandler()
	console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
	logger.addHandler(console_handler)

	return logger



