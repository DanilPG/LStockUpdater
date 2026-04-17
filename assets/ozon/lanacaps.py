import os
import sys
import requests
import base64
import traceback

# Добавляем путь к modules для импорта history
# Проверяем несколько возможных путей
script_dir = os.path.dirname(os.path.abspath(__file__))
possible_paths = [
    os.path.join(script_dir, '..', '..'),  # assets/ozon -> корень проекта
    os.path.join(os.getcwd()),              # Текущая рабочая директория
    os.path.dirname(os.path.dirname(script_dir)),  # Еще один уровень вверх
]

for path in possible_paths:
    if os.path.exists(os.path.join(path, 'modules')):
        sys.path.insert(0, path)
        break

def main():
    try:

        MS_LOGIN = "admin@sales1050"
        MS_PASS = "04121987Alexey"
        OZON_CLIENT_ID = "1534939"
        OZON_API_KEY = "bc4a6e74-2aba-4e43-ae7f-6e5b3938f1c5"

        # Для каждого склада в своих .py файлах ставь свой warehouse_id
        OZON_WAREHOUSE_ID = 1020005000457414
        SELLER_NAME = "Lana Caps"
        MARKETPLACE = "ozon"

        # === Авторизация ===
        credentials = f"{MS_LOGIN}:{MS_PASS}"
        b64_credentials = base64.b64encode(credentials.encode()).decode()

        MS_HEADERS = {
            "Authorization": f"Basic {b64_credentials}",
            "Accept-Encoding": "gzip",
            "Content-Type": "application/json"
        }

        OZON_HEADERS = {
            "Client-Id": OZON_CLIENT_ID,
            "Api-Key": OZON_API_KEY,
            "Content-Type": "application/json"
        }

        # === 1. Получаем остатки из МойСклад ===
        def get_ms_stock():
            all_rows = []
            limit = 1000
            offset = 0

            while True:
                print(f"> MS: загружаю страницу offset={offset}...")
                url = "https://api.moysklad.ru/api/remap/1.2/entity/assortment"
                params = {"limit": limit, "offset": offset}

                # Повторяем попытки получения текущей страницы до успеха или исчерпания лимита
                max_attempts = 5
                resp = None
                for attempt in range(1, max_attempts + 1):
                    try:
                        resp = requests.get(url, headers=MS_HEADERS, params=params, timeout=60)
                        if resp.status_code == 200:
                            break
                        else:
                            err = f"Ошибка МойСклад: {resp.status_code} - {resp.text}"
                            if attempt == max_attempts:
                                raise Exception(err)
                    except requests.exceptions.RequestException as e:
                        if attempt == max_attempts:
                            raise Exception(f"Ошибка соединения с МойСклад после {max_attempts} попыток: {e}")
                    import time as _t
                    _t.sleep(2 * attempt)

                data = resp.json()
                rows = data.get("rows", [])
                if not rows:
                    break

                for row in rows:
                    code = row.get("code") or row.get("id")
                    qty = row.get("stock", 0) - row.get("reserve", 0)
                    all_rows.append({"offer_id": code, "stock": qty})

                print(f"[OK] MS: offset={offset}, всего {len(all_rows)} товаров")

                if len(rows) < limit:
                    break
                offset += limit

            return all_rows

        # === 2. Получаем список offer_id с Ozon ===
        def get_ozon_offers():
            url = "https://api-seller.ozon.ru/v3/product/list"
            limit = 1000
            last_id = ""
            offers = []

            while True:
                payload = {"filter": {"visibility": "ALL"}, "last_id": last_id, "limit": limit}
                # Надёжные попытки с тайм-аутом и бэкоффом
                max_attempts = 3
                for attempt in range(1, max_attempts + 1):
                    try:
                        resp = requests.post(url, headers=OZON_HEADERS, json=payload, timeout=60)
                        if resp.status_code == 200:
                            break
                        else:
                            err = f"Ошибка Ozon: {resp.status_code} - {resp.text}"
                            if attempt == max_attempts:
                                raise Exception(err)
                    except requests.exceptions.RequestException as e:
                        if attempt == max_attempts:
                            raise Exception(e)
                    import time as _t
                    _t.sleep(2 * attempt)

                data = resp.json()
                items = data.get("result", {}).get("items", [])
                if not items:
                    break

                offers.extend([i.get("offer_id") for i in items if i.get("offer_id")])
                last_id = data.get("result", {}).get("last_id", "")
                if not last_id:
                    break

            return set(offers)

        # === 3. Получаем текущие остатки с Ozon ===
        def get_current_ozon_stocks(ozon_offers):
            """Получает текущие остатки с Ozon для всех товаров"""
            current_stocks = {}
            batch_size = 100
            offer_list = list(ozon_offers)
            cursor = ""
            
            while True:
                payload = {
                    "filter": {
                        "offer_id": offer_list[:1000]  # API v4 принимает до 1000 offer_id
                    },
                    "limit": 1000,
                    "cursor": cursor
                }
                url = "https://api-seller.ozon.ru/v4/product/info/stocks"
                
                try:
                    resp = requests.post(url, headers=OZON_HEADERS, json=payload, timeout=60)
                    if resp.status_code == 200:
                        data = resp.json()
                        items = data.get("items", [])
                        for item in items:
                            offer_id = item.get("offer_id")
                            stocks = item.get("stocks", [])
                            # Ищем остаток для типа fbs (склад продавца)
                            for stock in stocks:
                                if stock.get("type") == "fbs":
                                    current_stocks[offer_id] = stock.get("present", 0)
                                    break
                        
                        cursor = data.get("cursor", "")
                        if not cursor or not items:
                            break
                    else:
                        print(f"[WARNING] API вернул статус {resp.status_code}")
                        break
                except Exception as e:
                    print(f"[WARNING] Не удалось получить текущие остатки: {e}")
                    break
            
            print(f"[DEBUG] Получено текущих остатков для {len(current_stocks)} из {len(offer_list)} товаров")
            return current_stocks

        # === 4. Обновляем остатки на Ozon ===
        def update_ozon_stock(ms_stock, ozon_offers, current_stocks):
            # Если остаток отрицательный - ставим 0, иначе передаем как есть
            stock_list = [
                {"offer_id": item["offer_id"], "stock": max(0, item["stock"])} 
                for item in ms_stock 
                if item["offer_id"] in ozon_offers
            ]
            print(f"> К обновлению: {len(stock_list)} товаров")

            # Собираем данные для истории
            history_items = []

            batch_size = 100
            for i in range(0, len(stock_list), batch_size):
                batch = stock_list[i:i + batch_size]
                payload = {
                    "stocks": [
                        {"offer_id": item["offer_id"], "stock": item["stock"], "warehouse_id": OZON_WAREHOUSE_ID}
                        for item in batch
                    ]
                }
                url = "https://api-seller.ozon.ru/v2/products/stocks"
                try:
                    resp = requests.post(url, headers=OZON_HEADERS, json=payload, timeout=60)
                    if resp.status_code == 200:
                        print(f"[OK] Батч {i//batch_size + 1}: {len(batch)} товаров")
                        # Добавляем данные в историю
                        for item in batch:
                            offer_id = item["offer_id"]
                            new_stock = item["stock"]
                            old_stock = current_stocks.get(offer_id, 0)
                            history_items.append({
                                "sku": offer_id,  # offer_id используется как SKU (артикул)
                                "old_stock": old_stock,
                                "new_stock": new_stock
                            })
                    else:
                        print(f"[ERROR] Ошибка батча {i//batch_size + 1}: {resp.status_code} - {resp.text}")
                        # Продолжаем с следующим батчем вместо остановки
                        continue
                except requests.exceptions.RequestException as e:
                    print(f"[ERROR] Сетевая ошибка в батче {i//batch_size + 1}: {e}")
                    # Продолжаем с следующим батчем
                    continue
            
            return history_items

        # === Основной процесс ===
        ms_stock = get_ms_stock()
        ozon_offers = get_ozon_offers()
        current_stocks = get_current_ozon_stocks(ozon_offers)
        history_items = update_ozon_stock(ms_stock, ozon_offers, current_stocks)

        # Сохраняем историю
        try:
            from modules.history import add_action
            add_action("update", MARKETPLACE, SELLER_NAME, history_items)
            print(f"[OK] История сохранена: {len(history_items)} товаров")
        except Exception as e:
            print(f"[WARNING] Не удалось сохранить историю: {e}")

        print("\n[OK] Остатки успешно обновлены!")

    except Exception as e:
        with open("error_log.txt", "a", encoding="utf-8") as f:
            f.write("Ошибка:\n")
            f.write(str(e) + "\n")
            f.write(traceback.format_exc() + "\n")
            f.write("="*50 + "\n")
        print(f"\n[ERROR] Ошибка: {e}. Подробности в error_log.txt")

	# Убрано ожидание Enter для автоматического запуска из приложения

if __name__ == "__main__":
    main()
