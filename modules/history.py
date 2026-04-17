import json
import os
from datetime import datetime
from typing import Dict, List, Any
from .config import APP_DIR


HISTORY_PATH = os.path.join(APP_DIR, "history.json")


def ensure_history_file() -> None:
    """Создаёт файл истории, если он не существует"""
    if not os.path.isdir(APP_DIR):
        os.makedirs(APP_DIR, exist_ok=True)
    if not os.path.isfile(HISTORY_PATH):
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)


def load_history() -> List[Dict[str, Any]]:
    """Загружает историю действий"""
    ensure_history_file()
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_history(history: List[Dict[str, Any]]) -> None:
    """Сохраняет историю действий"""
    ensure_history_file()
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def add_action(
    action_type: str,  # "update" или "reset"
    marketplace: str,  # "ozon", "wb", "yandex"
    seller: str,  # название магазина
    items: List[Dict[str, Any]]  # список товаров с полями: offer_id, old_stock, new_stock
) -> None:
    """
    Добавляет запись о действии в историю
    
    Args:
        action_type: тип действия ("update" или "reset")
        marketplace: маркетплейс ("ozon", "wb", "yandex")
        seller: название магазина
        items: список товаров с полями offer_id, old_stock, new_stock
    """
    history = load_history()
    
    record = {
        "date": datetime.now().isoformat(timespec="seconds"),
        "action_type": action_type,
        "marketplace": marketplace,
        "seller": seller,
        "items_count": len(items),
        "items": items
    }
    
    history.append(record)
    save_history(history)


def get_history() -> List[Dict[str, Any]]:
    """Возвращает всю историю"""
    return load_history()


def clear_history() -> None:
    """Очищает всю историю"""
    save_history([])


def clear_history_by_date_range(date_from, date_to) -> int:
    """
    Удаляет записи истории за указанный диапазон дат
    
    Args:
        date_from: начальная дата (datetime.date)
        date_to: конечная дата (datetime.date)
    
    Returns:
        Количество удаленных записей
    """
    history = load_history()
    original_count = len(history)
    
    filtered_history = []
    for record in history:
        date_str = record.get("date", "")
        try:
            record_date = datetime.fromisoformat(date_str).date()
            # Оставляем записи вне диапазона
            if not (date_from <= record_date <= date_to):
                filtered_history.append(record)
        except:
            # Если не удалось распарсить дату, оставляем запись
            filtered_history.append(record)
    
    save_history(filtered_history)
    return original_count - len(filtered_history)
