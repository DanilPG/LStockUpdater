import requests
import time
import sys
import os

# Добавляем путь к modules для импорта history
# Проверяем несколько возможных путей
script_dir = os.path.dirname(os.path.abspath(__file__))
possible_paths = [
    os.path.join(script_dir, '..', '..', '..'),  # assets/wb/reset -> корень проекта
    os.path.join(os.getcwd()),                    # Текущая рабочая директория
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))),  # Еще один уровень вверх
]

for path in possible_paths:
    if os.path.exists(os.path.join(path, 'modules')):
        sys.path.insert(0, path)
        break

from modules.history import add_action

# === Настройки ===
WB_KEY = "eyJhbGciOiJFUzI1NiIsImtpZCI6IjIwMjYwMzAydjEiLCJ0eXAiOiJKV1QifQ.eyJhY2MiOjEsImVudCI6MSwiZXhwIjoxNzkwOTQ1MjM2LCJpZCI6IjAxOWQ1MGNmLTAwOGYtNzFiZS05OGM3LTk2ZGM4Y2UxODE2MiIsImlpZCI6MTIzMzkyOTAsIm9pZCI6NDIzMTY3MiwicyI6MTA0Miwic2lkIjoiYzY5MTA5NWQtNTI1NS00MTY2LWJmMjctMjFhNzVjNDkwZmIxIiwidCI6ZmFsc2UsInVpZCI6MTIzMzkyOTB9.FETUAOgbxbVZh2anuChMpR3Snn4anE1VeFvq0G9Q4YrLzhwM5fdPFT5QMoH06ELrz0j0RJubIAwB9A9-cYWzEg"
WB_WAREHOUSE_ID = "1189816"
SELLER_NAME = "Ярославцева"
MARKETPLACE = "wb"

# === Получаем все карточки WB ===
def get_all_wb_cards():
    headers = {
        "Authorization": WB_KEY,
        "Content-Type": "application/json"
    }
    url = "https://content-api.wildberries.ru/content/v2/get/cards/list"
    limit = 100
    cursor = {"limit": limit}
    settings = {"cursor": cursor, "filter": {"withPhoto": -1}}
    all_cards = []

    while True:
        resp = requests.post(url, headers=headers, json={"settings": settings})
        if resp.status_code != 200:
            raise Exception(f"Ошибка WB Content API: {resp.status_code} - {resp.text}")

        data = resp.json()
        cards = data.get("cards", [])
        all_cards.extend(cards)

        # Если карточек меньше лимита — значит всё выгрузили
        if len(cards) < limit:
            break

        # Обновляем курсор только если API вернул новый
        new_cursor = data.get("cursor", {})
        if not new_cursor.get("updatedAt") or not new_cursor.get("nmID"):
            break  # конец данных
        settings["cursor"] = {"limit": limit, **new_cursor}

        print(f"[OK] Загружено карточек: {len(all_cards)}")

    print(f"[OK] Всего карточек WB: {len(all_cards)}")
    return all_cards


# === Получаем текущие остатки ===
def get_current_wb_stocks(wb_cards):
    headers = {
        "Authorization": WB_KEY,
        "Content-Type": "application/json"
    }
    url = f"https://marketplace-api.wildberries.ru/api/v3/stocks/{WB_WAREHOUSE_ID}"
    batch_size = 100
    sku_list = []
    current_stocks = {}

    for card in wb_cards:
        for size in card.get("sizes", []):
            for sku in size.get("skus", []):
                sku_list.append(str(sku))

    print(f"[OK] Получаем текущие остатки для {len(sku_list)} SKU...")

    for i in range(0, len(sku_list), batch_size):
        batch = sku_list[i:i+batch_size]
        payload = {"skus": batch}
        resp = requests.post(url, headers=headers, json=payload)
        if resp.status_code == 200:
            data = resp.json()
            for stock in data.get("stocks", []):
                current_stocks[stock["sku"]] = stock["amount"]
        else:
            print(f"[ERROR] Ошибка получения остатков: {resp.status_code} {resp.text}")
        time.sleep(0.2)

    print(f"[OK] Получены остатки для {len(current_stocks)} SKU")
    return current_stocks


# === Обнуляем остатки ===
def reset_wb_stock(wb_cards, current_stocks):
    headers = {
        "Authorization": WB_KEY,
        "Content-Type": "application/json"
    }
    url = f"https://marketplace-api.wildberries.ru/api/v3/stocks/{WB_WAREHOUSE_ID}"
    batch_size = 50
    sku_list = []
    history_items = []

    for card in wb_cards:
        for size in card.get("sizes", []):
            for sku in size.get("skus", []):
                sku_list.append(str(sku))

    print(f"[OK] Всего SKU для обнуления: {len(sku_list)}")

    for i in range(0, len(sku_list), batch_size):
        batch = sku_list[i:i+batch_size]
        payload = {"stocks": [{"sku": sku, "amount": 0} for sku in batch]}
        resp = requests.put(url, headers=headers, json=payload)
        if resp.status_code == 204:
            print(f"[OK] Обнулено {min(i+batch_size, len(sku_list))}/{len(sku_list)} SKU")
            # Добавляем в историю
            for sku in batch:
                old_stock = current_stocks.get(sku, 0)
                if old_stock != 0:  # Записываем только те, что изменились
                    history_items.append({
                        "sku": sku,
                        "old_stock": old_stock,
                        "new_stock": 0
                    })
        else:
            print(f"[ERROR] Ошибка: {resp.status_code} {resp.text}")
        time.sleep(0.3)  # чтобы не словить лимит API

    return history_items

# === Основной процесс ===
def main():
    wb_cards = get_all_wb_cards()
    current_stocks = get_current_wb_stocks(wb_cards)
    history_items = reset_wb_stock(wb_cards, current_stocks)
    print("[OK] Все остатки успешно обнулены!")
    
    # Сохраняем историю
    if history_items:
        add_action("reset", MARKETPLACE, SELLER_NAME, history_items)
        print(f"[OK] История сохранена: {len(history_items)} записей")

if __name__ == "__main__":
    main()
