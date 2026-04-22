import os
import sys
import requests
import base64
from datetime import datetime, timezone, timedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Добавляем путь к modules для импорта history
# Проверяем несколько возможных путей
script_dir = os.path.dirname(os.path.abspath(__file__))
possible_paths = [
    os.path.join(script_dir, '..', '..'),  # assets/yandex -> корень проекта
    os.path.join(os.getcwd()),              # Текущая рабочая директория
    os.path.dirname(os.path.dirname(script_dir)),  # Еще один уровень вверх
]

for path in possible_paths:
    if os.path.exists(os.path.join(path, 'modules')):
        sys.path.insert(0, path)
        break

# === 1. Настройки ===
YANDEX_TOKEN = "ACMA:G28rLKTHoyIWkTFI5lOoxFMS4GEdnNbGEpHW5BW7:8894c523"
MS_LOGIN = "admin@sales1050"
MS_PASS = "04121987Alexey"
SELLER_NAME = "ИП Краснова, ИП Шифман"
MARKETPLACE = "yandex"

if not YANDEX_TOKEN:
    raise ValueError("Токен Яндекс.Маркета не найден! Проверь .env")
if not MS_LOGIN or not MS_PASS:
    raise ValueError("Логин/пароль МойСклад не найдены! Проверь .env")

# === 2. Основные параметры ===
BUSINESS_ID = 830802
CAMPAIGN_ID = 21632562
BATCH_SIZE = 50  # уменьшаем для стабильности при большом количестве товаров

# === 3. Функция логов ===
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# === 4. Создаем сессию с повторными попытками ===
def create_session():
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=frozenset(['GET', 'POST', 'PUT'])
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    return session

# === 5. Получаем остатки из МойСклад с повторными попытками ===
def get_ms_stock():
    log("> Получаем остатки из МойСклад...")
    all_stock = {}
    limit = 1000
    offset = 0
    credentials = f"{MS_LOGIN}:{MS_PASS}"
    b64_credentials = base64.b64encode(credentials.encode()).decode()
    headers = {
        "Authorization": f"Basic {b64_credentials}",
        "Accept-Encoding": "gzip",
        "Content-Type": "application/json"
    }

    while True:
        log(f"> Загружаем страницу offset={offset}...")
        url = "https://api.moysklad.ru/api/remap/1.2/entity/assortment"
        params = {"limit": limit, "offset": offset}
        
        # Повторные попытки для каждого запроса
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Увеличиваем таймаут: 30 сек на соединение + 90 сек на чтение
                resp = requests.get(url, headers=headers, params=params, timeout=(30, 90))
                if resp.status_code != 200:
                    if attempt < max_retries - 1:
                        log(f"[WARNING] Ошибка МойСклад (попытка {attempt + 1}/{max_retries}): {resp.status_code}")
                        import time
                        time.sleep(2)  # Пауза перед повторной попыткой
                        continue
                    else:
                        raise Exception(f"Ошибка МойСклад: {resp.status_code} - {resp.text}")
                break  # Успешный запрос
            except requests.exceptions.Timeout as e:
                if attempt < max_retries - 1:
                    log(f"[WARNING] Таймаут МойСклад (попытка {attempt + 1}/{max_retries})")
                    import time
                    time.sleep(2)
                    continue
                else:
                    raise Exception(f"Таймаут соединения с МойСклад после {max_retries} попыток: {e}")
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    log(f"[WARNING] Ошибка соединения с МойСклад (попытка {attempt + 1}/{max_retries}): {e}")
                    import time
                    time.sleep(2)  # Пауза перед повторной попыткой
                    continue
                else:
                    log(f"[ERROR] Ошибка соединения с МойСклад после {max_retries} попыток: {e}")
                    log(f"[INFO] Продолжаем с уже загруженными данными: {len(all_stock)} товаров")
                    return all_stock
        data = resp.json()
        rows = data.get("rows", [])
        if not rows:
            break
        for row in rows:
            code = row.get("code") or row.get("id")
            qty = row.get("stock", 0) - row.get("reserve", 0)
            all_stock[code] = max(0, qty)
        log(f"[OK] MS: offset={offset}, всего загружено {len(all_stock)} товаров")
        if len(rows) < limit:
            break
        offset += limit
    return all_stock

# === 6. Получаем все товары с ЯМ ===
def get_ym_offers(session):
    log("> Получаем товары Яндекс.Маркет...")
    all_offers = {}
    page_token = None
    page_num = 1
    headers = {"Api-Key": YANDEX_TOKEN, "Content-Type": "application/json"}
    url_offers = f"https://api.partner.market.yandex.ru/v2/businesses/{BUSINESS_ID}/offer-mappings"

    while True:
        params = {"page_size": 1000}
        if page_token:
            params["page_token"] = page_token
        response = session.post(url_offers, headers=headers, json={}, params=params, timeout=60)
        if response.status_code != 200:
            raise Exception(f"Ошибка загрузки товаров YM: {response.status_code} - {response.text}")
        data = response.json()
        offers = data.get("result", {}).get("offerMappings", [])
        for offer in offers:
            sku = offer.get("offer", {}).get("offerId")
            if sku:
                all_offers[sku] = offer
        log(f"[OK] Страница {page_num}: найдено {len(offers)} товаров")
        page_token = data.get("result", {}).get("paging", {}).get("nextPageToken")
        if not page_token:
            break
        page_num += 1
    log(f"[OK] Всего найдено товаров на ЯМ: {len(all_offers)}")
    if len(all_offers) == 0:
        log("[WARNING] На Яндекс.Маркете не найдено товаров!")
    return all_offers

# === 7. Получаем текущие остатки с ЯМ ===
def get_current_ym_stocks(session, ym_offers):
    """Получает текущие остатки с Яндекс.Маркета для всех товаров"""
    log("> Получаем текущие остатки с Яндекс.Маркет...")
    current_stocks = {}
    headers = {"Api-Key": YANDEX_TOKEN, "Content-Type": "application/json"}
    url_stocks = f"https://api.partner.market.yandex.ru/v2/campaigns/{CAMPAIGN_ID}/offers/stocks"
    
    # Получаем все SKU
    all_skus = list(ym_offers.keys())
    
    # Получаем текущие остатки пачками
    batch_size = 1000
    for i in range(0, len(all_skus), batch_size):
        batch = all_skus[i:i + batch_size]
        try:
            params = {"skus": ",".join(batch)}
            resp = session.get(url_stocks, headers=headers, params=params, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                for stock_item in data.get("result", {}).get("stocks", []):
                    sku = stock_item.get("sku")
                    items = stock_item.get("items", [])
                    if items:
                        current_stocks[sku] = items[0].get("count", 0)
        except Exception as e:
            log(f"[WARNING] Не удалось получить текущие остатки для батча {i//batch_size + 1}: {e}")
    
    log(f"[OK] Получено текущих остатков: {len(current_stocks)} товаров")
    return current_stocks

# === 8. Обновление остатков пакетами с сессией и таймаутом ===
def update_ym_stock(session, ms_stock, ym_offers, current_stocks):
    if len(ms_stock) == 0:
        log("[WARNING] Нет данных из МойСклад для обновления!")
        return []
    if len(ym_offers) == 0:
        log("[WARNING] Нет товаров на Яндекс.Маркете для обновления!")
        return []
    
    common_skus = sorted(set(ms_stock.keys()) & set(ym_offers.keys()))
    log(f"> К обновлению: {len(common_skus)} товаров")
    
    if len(common_skus) == 0:
        log("[WARNING] Нет общих товаров между МойСклад и Яндекс.Маркет!")
        return []
    
    # Собираем данные для истории
    history_items = []
    
    headers = {"Api-Key": YANDEX_TOKEN, "Content-Type": "application/json"}
    url_stocks = f"https://api.partner.market.yandex.ru/v2/campaigns/{CAMPAIGN_ID}/offers/stocks"

    for i in range(0, len(common_skus), BATCH_SIZE):
        batch_skus = common_skus[i:i+BATCH_SIZE]
        payload = {"skus": []}
        moscow_time = datetime.now(timezone(timedelta(hours=3))).isoformat()
        for sku in batch_skus:
            new_stock = int(ms_stock[sku])
            old_stock = current_stocks.get(sku, 0)
            payload["skus"].append({
                "sku": sku,
                "items": [{"count": new_stock, "updatedAt": moscow_time}]
            })
            # Добавляем данные в историю
            history_items.append({
                "sku": sku,  # sku используется как артикул
                "old_stock": old_stock,
                "new_stock": new_stock
            })
        # Повторные попытки для каждого батча
        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = session.put(url_stocks, headers=headers, json=payload, timeout=60)
                if resp.status_code == 200:
                    log(f"[OK] Обновлено товаров: {min(i+BATCH_SIZE, len(common_skus))}/{len(common_skus)}")
                    break  # Успешный запрос
                else:
                    if attempt < max_retries - 1:
                        log(f"[WARNING] Ошибка в батче {i//BATCH_SIZE+1} (попытка {attempt + 1}/{max_retries}): {resp.status_code}")
                        import time
                        time.sleep(2)  # Пауза перед повторной попыткой
                        continue
                    else:
                        log(f"[ERROR] Ошибка в батче {i//BATCH_SIZE+1}: {resp.status_code} - {resp.text}")
                        break
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    log(f"[WARNING] Сетевая ошибка в батче {i//BATCH_SIZE+1} (попытка {attempt + 1}/{max_retries}): {e}")
                    import time
                    time.sleep(2)  # Пауза перед повторной попыткой
                    continue
                else:
                    log(f"[ERROR] Сетевая ошибка в батче {i//BATCH_SIZE+1}: {e}")
                    break

    log("[OK] Все остатки успешно обновлены!")
    return history_items

# === 9. Основной процесс ===
if __name__ == "__main__":
    try:
        session = create_session()
        ms_stock = get_ms_stock()
        ym_offers = get_ym_offers(session)
        current_stocks = get_current_ym_stocks(session, ym_offers)
        history_items = update_ym_stock(session, ms_stock, ym_offers, current_stocks)

        # Сохраняем историю
        try:
            from modules.history import add_action
            add_action("update", MARKETPLACE, SELLER_NAME, history_items)
            log(f"[OK] История сохранена: {len(history_items)} товаров")
        except Exception as e:
            log(f"[WARNING] Не удалось сохранить историю: {e}")
    except Exception as e:
        log(f"[ERROR] Ошибка: {e}")
