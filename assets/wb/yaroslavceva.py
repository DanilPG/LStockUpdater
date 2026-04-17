import os
import sys
import requests
import base64

# Добавляем путь к modules для импорта history
# Проверяем несколько возможных путей
script_dir = os.path.dirname(os.path.abspath(__file__))
possible_paths = [
    os.path.join(script_dir, '..', '..'),  # assets/wb -> корень проекта
    os.path.join(os.getcwd()),              # Текущая рабочая директория
    os.path.dirname(os.path.dirname(script_dir)),  # Еще один уровень вверх
]

for path in possible_paths:
    if os.path.exists(os.path.join(path, 'modules')):
        sys.path.insert(0, path)
        break

# === Настройки ===
MS_LOGIN = "admin@sales1050"
MS_PASS = "04121987Alexey"
WB_KEY = "eyJhbGciOiJFUzI1NiIsImtpZCI6IjIwMjYwMzAydjEiLCJ0eXAiOiJKV1QifQ.eyJhY2MiOjEsImVudCI6MSwiZXhwIjoxNzkwOTQ1MjM2LCJpZCI6IjAxOWQ1MGNmLTAwOGYtNzFiZS05OGM3LTk2ZGM4Y2UxODE2MiIsImlpZCI6MTIzMzkyOTAsIm9pZCI6NDIzMTY3MiwicyI6MTA0Miwic2lkIjoiYzY5MTA5NWQtNTI1NS00MTY2LWJmMjctMjFhNzVjNDkwZmIxIiwidCI6ZmFsc2UsInVpZCI6MTIzMzkyOTB9.FETUAOgbxbVZh2anuChMpR3Snn4anE1VeFvq0G9Q4YrLzhwM5fdPFT5QMoH06ELrz0j0RJubIAwB9A9-cYWzEg"
WB_WAREHOUSE_ID = "1189816"
SELLER_NAME = "Ярославцева"
MARKETPLACE = "wb"

# === Авторизация МойСклад ===
credentials = f"{MS_LOGIN}:{MS_PASS}"
b64_credentials = base64.b64encode(credentials.encode()).decode()
MS_HEADERS = {
    "Authorization": f"Basic {b64_credentials}",
    "Accept-Encoding": "gzip",
    "Content-Type": "application/json"
}

# === 1. Получаем все товары из МойСклад ===
def get_all_ms_items():
    limit = 1000
    offset = 0
    ms_items = {}

    while True:
        print(f"> МойСклад: загружаю offset={offset}...")
        url = "https://api.moysklad.ru/api/remap/1.2/entity/assortment"
        params = {"limit": limit, "offset": offset}
        try:

            resp = requests.get(url, headers=MS_HEADERS, params=params, timeout=60)

            if resp.status_code != 200:

                raise Exception(f"Ошибка МойСклад: {resp.status_code} - {resp.text}")

        except requests.exceptions.RequestException as e:

            print(f"[ERROR] Ошибка соединения с МойСклад: {e}")

            print(f"[INFO] Продолжаем с уже загруженными данными: {len(ms_items)} товаров")

            break

        rows = resp.json().get("rows", [])
        if not rows:
            break

        for row in rows:
            code = row.get("code")
            stock = max(0, row.get("stock", 0) - row.get("reserve", 0))
            barcodes = []
            for b in row.get("barcodes", []):
                barcodes.extend(b.values())
            ms_items[code] = {"stock": stock, "barcodes": barcodes}

        if len(rows) < limit:
            break
        offset += limit

    print(f"[OK] Всего товаров МойСклад: {len(ms_items)}")
    return ms_items

# === 2. Получаем все карточки WB ===
def get_all_wb_cards():
    headers = {
        "Authorization": WB_KEY,
        "Content-Type": "application/json"
    }
    url = "https://content-api.wildberries.ru/content/v2/get/cards/list"
    cursor = {"limit": 100}
    settings = {"cursor": cursor, "filter": {"withPhoto": -1}}
    all_cards = []

    while True:
        payload = {"settings": settings}
        resp = requests.post(url, headers=headers, json=payload)
        if resp.status_code != 200:
            raise Exception(f"Ошибка WB Content API: {resp.status_code} - {resp.text}")

        data = resp.json()
        cards = data.get("cards", [])
        all_cards.extend(cards)

        if len(cards) < cursor["limit"]:
            break

        response_cursor = data.get("cursor", {})
        cursor["updatedAt"] = response_cursor.get("updatedAt")
        cursor["nmID"] = response_cursor.get("nmID")
        settings["cursor"] = cursor

        print(f"[OK] Загружено карточек WB: {len(all_cards)}")

    print(f"[OK] Всего карточек WB: {len(all_cards)}")
    return all_cards

# === 3. Получаем текущие остатки WB ===
def get_current_wb_stocks(wb_cards):
    """Получает текущие остатки с WB для всех SKU"""
    headers = {
        "Authorization": WB_KEY,
        "Content-Type": "application/json"
    }
    url = f"https://marketplace-api.wildberries.ru/api/v3/stocks/{WB_WAREHOUSE_ID}"
    
    # Собираем все SKU
    all_skus = []
    for card in wb_cards:
        for size in card.get("sizes", []):
            for sku in size.get("skus", []):
                all_skus.append(str(sku))
    
    # Получаем текущие остатки
    current_stocks = {}
    batch_size = 1000
    for i in range(0, len(all_skus), batch_size):
        batch = all_skus[i:i + batch_size]
        try:
            resp = requests.get(url, headers=headers, params={"skus": ",".join(batch)}, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                for stock_item in data.get("stocks", []):
                    sku = stock_item.get("sku")
                    amount = stock_item.get("amount", 0)
                    current_stocks[sku] = amount
        except Exception as e:
            print(f"[WARNING] Не удалось получить текущие остатки для батча {i//batch_size + 1}: {e}")
    
    return current_stocks

# === 4. Формируем список SKU для обновления ===
def prepare_skus_to_update(ms_items, wb_cards):
    sku_amount_pairs = []
    card_ids_set = {}

    for card in wb_cards:
        card_updated = False
        for size in card.get("sizes", []):
            for sku in size.get("skus", []):
                for ms_item in ms_items.values():
                    if sku in ms_item["barcodes"]:
                        sku_amount_pairs.append((sku, ms_item["stock"]))
                        card_ids_set[str(sku)] = ms_item["stock"]
                        card_updated = True
        if card_updated:
            pass

    print(f"[OK] Найдено уникальных SKU для обновления: {len(sku_amount_pairs)}")
    return sku_amount_pairs

# === 5. Обновляем остатки на WB пакетами по 50 SKU ===
def update_wb_stock_batch(sku_amount_pairs, current_stocks):
    headers = {
        "Authorization": WB_KEY,
        "Content-Type": "application/json"
    }
    url = f"https://marketplace-api.wildberries.ru/api/v3/stocks/{WB_WAREHOUSE_ID}"
    batch_size = 50

    # Собираем данные для истории
    history_items = []

    total_skus = len(sku_amount_pairs)
    for i in range(0, total_skus, batch_size):
        batch = sku_amount_pairs[i:i+batch_size]
        payload_stocks = []
        for sku, amount in batch:
            if sku and isinstance(amount, (int, float)) and amount >= 0:
                payload_stocks.append({"sku": str(sku), "amount": int(amount)})
                # Добавляем данные в историю
                old_stock = current_stocks.get(str(sku), 0)
                history_items.append({
                    "sku": str(sku),  # sku используется как артикул
                    "old_stock": old_stock,
                    "new_stock": int(amount)
                })

        if not payload_stocks:
            continue

        payload = {"stocks": payload_stocks}
        resp = requests.put(url, headers=headers, json=payload)
        if resp.status_code == 204:
            print(f"[OK] Обновлено {min(i+batch_size, total_skus)}/{total_skus} SKUs")
        else:
            raise Exception(f"Ошибка обновления: {resp.status_code} {resp.text}")
    
    return history_items

# === Основной процесс ===
def main():
    ms_items = get_all_ms_items()
    wb_cards = get_all_wb_cards()
    current_stocks = get_current_wb_stocks(wb_cards)
    sku_amount_pairs = prepare_skus_to_update(ms_items, wb_cards)
    history_items = update_wb_stock_batch(sku_amount_pairs, current_stocks)

    # Сохраняем историю
    try:
        from modules.history import add_action
        add_action("update", MARKETPLACE, SELLER_NAME, history_items)
        print(f"[OK] История сохранена: {len(history_items)} товаров")
    except Exception as e:
        print(f"[WARNING] Не удалось сохранить историю: {e}")

if __name__ == "__main__":
    main()
