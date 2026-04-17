from datetime import datetime
import glob
import os
from typing import Dict, List, Optional

from .config import load_config, save_config
from .app_logger import get_logger
from .script_runner import run_stock_script


def _get_project_root() -> str:
	# Проектная корневая папка = один уровень вверх от modules/
	return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def list_stores_from_assets() -> Dict[str, str]:
	# Нормализуем путь к assets/ozon независимо от cwd
	project_root = _get_project_root()
	base = os.path.join(project_root, "assets", "ozon")
	if not os.path.isdir(base):
		# fallback: относительный путь от cwd
		base = os.path.join(os.getcwd(), "assets", "ozon")
	result: Dict[str, str] = {}
	for path in glob.glob(os.path.join(base, "*.py")):
		name = os.path.splitext(os.path.basename(path))[0]
		result[name] = path
	return result


def update_stocks(selected_stores: Optional[List[str]] = None) -> str:
	logger = get_logger()
	config = load_config()
	stores_meta: Dict[str, Dict] = config.setdefault("stores", {}).setdefault("ozon", {})
	available = list_stores_from_assets()
	stores_to_update = selected_stores or list(available.keys())
	stores_to_update = [s for s in stores_to_update if s in available]
	if not stores_to_update:
		return "Нет выбранных магазинов Ozon"

	results: List[str] = []
	for store in stores_to_update:
		logger.info("Обновление остатков Ozon (скрипт): %s", store)
		path = available[store]
		rc, out, err = run_stock_script(path, stdin_newline=True)
		stdout = (out or "").strip()
		stderr = (err or "").strip()
		if rc != 0:
			logger.error("Скрипт %s завершился с ошибкой: %s", store, stderr)
			results.append(f"❌ {store}: ошибка. См. ниже.\n{stderr}")
			continue
		stores_meta.setdefault(store, {})["last_updated"] = datetime.now().isoformat(timespec="seconds")
		# Optionally parse count from output
		stores_meta[store].setdefault("item_count", 0)
		# include some of the script output for transparency
		tail = "\n".join(stdout.splitlines()[-10:]) if stdout else ""
		results.append(f"✅ {store}: выполнено.\n{tail}")

	save_config(config)
	return "\n".join(results) if results else "Нет результатов"


def reset_stocks(selected_stores: Optional[List[str]] = None) -> str:
	logger = get_logger()
	if not selected_stores:
		return "Нет выбранных магазинов Ozon"

	# Ищем скрипты обнуления по соглашению:
	# 1) assets/ozon/<store>_reset.py
	# 2) assets/ozon/reset/<store>.py
	project_root = _get_project_root()
	assets_dir = os.path.join(project_root, "assets", "ozon")
	results: List[str] = []
	for store in selected_stores:
		store_key = (store or "").strip()
		candidates = [
			os.path.join(assets_dir, f"{store_key}_reset.py"),
			os.path.join(assets_dir, "reset", f"{store_key}.py"),
			os.path.join(assets_dir, f"{store_key.lower()}_reset.py"),
			os.path.join(assets_dir, "reset", f"{store_key.lower()}.py"),
		]
		script_path = next((p for p in candidates if os.path.isfile(p)), None)
		if not script_path:
			results.append(
				"❌ "
				+ store_key
				+ ": не найден файл обнуления. Искомые пути:\n- "
				+ "\n- ".join(candidates)
			)
			continue
		logger.info("Обнуление остатков Ozon (скрипт): %s", store)
		rc, out, err = run_stock_script(script_path, stdin_newline=True)
		stdout = (out or "").strip()
		stderr = (err or "").strip()
		if rc != 0:
			logger.error("Скрипт обнуления %s завершился с ошибкой: %s", store, stderr)
			results.append(f"❌ {store}: ошибка обнуления.\n{stderr}")
			continue
		results.append(f"✅ {store}: остатки обнулены.\n{os.linesep.join(stdout.splitlines()[-10:]) if stdout else ''}")

	return "\n".join(results) if results else "Нет результатов"



