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
    os.path.join(script_dir, '..', '..', '..'),  # assets/yandex/reset -> корень проекта
    os.path.join(os.getcwd()),                    # Текущая рабочая директория
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))),  # Еще один уровень вверх
]

for path in possible_paths:
    if os.path.exists(os.path.join(path, 'modules')):
        sys.path.insert(0, path)
        break

from modules.history import add_action

# === 1. Настройки ===
YANDEX_TOKEN = "ACMA:G28rLKTHoyIWkTFI5lOoxFMS4GEdnNbGEpHW5BW7:8894c523"  # токен ЯМ

if not YANDEX_TOKEN:
    raise ValueError("❌ Токен Яндекс.Маркета не найден!")

# === 2. Основные параметры ===
BUSINESS_ID = 830802         # твой businessId
CAMPAIGN_ID = 21632562       # твой campaignId
BATCH_SIZE = 100             # сколько товаров обновлять за раз
SELLER_NAME = "YM1"
MARKETPLACE = "yandex"

# === 3. Функция логов ===
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# === 4. Создаем сессию с повторными попытками ===
def create_session():
    session = requests.Session()
    retries = Retry(
        total=5,                  # количество повторных попыток
        backoff_factor=0.5,       # пауза между попытками
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=frozenset(['GET', 'POST', 'PUT'])
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    return session

# === 5. Получаем все товары с ЯМ ===
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
    return all_offers

# === 6. Получаем текущие остатки ===
def get_current_ym_stocks(session, ym_offers):
    log("> Получаем текущие остатки...")
    current_stocks = {}
    skus = list(ym_offers.keys())
    headers = {"Api-Key": YANDEX_TOKEN, "Content-Type": "application/json"}
    url_stocks = f"https://api.partner.market.yandex.ru/v2/campaigns/{CAMPAIGN_ID}/offers/stocks"
    
    for i in range(0, len(skus), BATCH_SIZE):
        batch_skus = skus[i:i+BATCH_SIZE]
        payload = {"skus": batch_skus}
        try:
            resp = session.post(url_stocks, headers=headers, json=payload, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                for stock in data.get("result", {}).get("stocks", []):
                    sku = stock.get("sku")
                    items = stock.get("items", [])
                    if items:
                        current_stocks[sku] = items[0].get("count", 0)
                    else:
                        current_stocks[sku] = 0
        except Exception as e:
            log(f"[ERROR] Ошибка получения остатков для батча {i//BATCH_SIZE+1}: {e}")
    
    log(f"[OK] Получены остатки для {len(current_stocks)} товаров")
    return current_stocks

# === 7. Обнуление остатков пакетами ===
def reset_ym_stock(session, ym_offers, current_stocks):
    skus_to_reset = list(ym_offers.keys())
    log(f"> Обнуление остатков: {len(skus_to_reset)} товаров")
    headers = {"Api-Key": YANDEX_TOKEN, "Content-Type": "application/json"}
    url_stocks = f"https://api.partner.market.yandex.ru/v2/campaigns/{CAMPAIGN_ID}/offers/stocks"
    history_items = []
    
    for i in range(0, len(skus_to_reset), BATCH_SIZE):
        batch_skus = skus_to_reset[i:i+BATCH_SIZE]
        payload = {"skus": []}
        moscow_time = datetime.now(timezone(timedelta(hours=3))).isoformat()
        for sku in batch_skus:
            payload["skus"].append({
                "sku": sku,
                "items": [{"count": 0, "updatedAt": moscow_time}]
            })
        # Повторные попытки для каждого батча
        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = session.put(url_stocks, headers=headers, json=payload, timeout=60)
                if resp.status_code == 200:
                    log(f"[OK] Обнулено товаров: {min(i+BATCH_SIZE, len(skus_to_reset))}/{len(skus_to_reset)}")
                    # Добавляем в историю
                    for sku in batch_skus:
                        old_stock = current_stocks.get(sku, 0)
                        if old_stock != 0:  # Записываем только те, что изменились
                            history_items.append({
                                "sku": sku,
                                "old_stock": old_stock,
                                "new_stock": 0
                            })
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

    log("[OK] Все остатки успешно обнулены!")
    return history_items

# === 8. Основной процесс ===
if __name__ == "__main__":
    try:
        session = create_session()
        ym_offers = get_ym_offers(session)
        current_stocks = get_current_ym_stocks(session, ym_offers)
        history_items = reset_ym_stock(session, ym_offers, current_stocks)
        
        # Сохраняем историю
        if history_items:
            add_action("reset", MARKETPLACE, SELLER_NAME, history_items)
            log(f"[OK] История сохранена: {len(history_items)} записей")
    except Exception as e:
        log(f"[ERROR] Ошибка: {e}")
