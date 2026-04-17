import json
import os
from typing import Any, Dict

APP_DIR = os.path.expanduser("~/.lstock")
CONFIG_PATH = os.path.join(APP_DIR, "config.json")

DEFAULT_CONFIG: Dict[str, Any] = {
	"stores": {
		"ozon": {},  # store_name -> { token, sellerId, last_updated, item_count }
		"wb": {},
		"yandex": {}
	}
}


def ensure_app_dir() -> None:
	if not os.path.isdir(APP_DIR):
		os.makedirs(APP_DIR, exist_ok=True)


def load_config() -> Dict[str, Any]:
	ensure_app_dir()
	if not os.path.isfile(CONFIG_PATH):
		save_config(DEFAULT_CONFIG)
		return DEFAULT_CONFIG.copy()
	try:
		with open(CONFIG_PATH, "r", encoding="utf-8") as f:
			return json.load(f)
	except Exception:
		return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any]) -> None:
	ensure_app_dir()
	with open(CONFIG_PATH, "w", encoding="utf-8") as f:
		json.dump(config, f, ensure_ascii=False, indent=2)



