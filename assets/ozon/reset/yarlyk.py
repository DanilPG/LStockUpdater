import os
import sys
import requests

# Добавляем путь к modules для импорта history
# Проверяем несколько возможных путей
script_dir = os.path.dirname(os.path.abspath(__file__))
possible_paths = [
    os.path.join(script_dir, '..', '..'),  # assets/ozon/reset -> корень проекта
    os.path.join(os.getcwd()),              # Текущая рабочая директория
    os.path.dirname(os.path.dirname(os.path.dirname(script_dir))),  # Еще один уровень вверх
]

for path in possible_paths:
    if os.path.exists(os.path.join(path, 'modules')):
        sys.path.insert(0, path)
        break

OZON_CLIENT_ID = "2303645"
OZON_API_KEY = "c4ebbc16-b435-4b0e-9e2d-70e55606b7ca"
OZON_WAREHOUSE_ID = 1020005000124539
SELLER_NAME = "Ярлык"
MARKETPLACE = "ozon"


def main():
	headers = {"Client-Id": OZON_CLIENT_ID, "Api-Key": OZON_API_KEY, "Content-Type": "application/json"}
	products = []
	last_id = ""
	
	# Сначала получаем текущие остатки
	current_stocks = {}
	while True:
		max_attempts = 3
		for attempt in range(1, max_attempts + 1):
			try:
				resp = requests.post(
					"https://api-seller.ozon.ru/v3/product/list",
					headers=headers,
					json={"filter": {"visibility": "ALL"}, "last_id": last_id, "limit": 1000},
					timeout=60,
				)
				resp.raise_for_status()
				break
			except requests.exceptions.RequestException:
				if attempt == max_attempts:
					raise
				import time as _t
				_t.sleep(2 * attempt)
		data = resp.json().get("result", {})
		items = data.get("items", [])
		if not items:
			break
		products.extend([i.get("offer_id") for i in items if i.get("offer_id")])
		last_id = data.get("last_id", "")
		if not last_id:
			break
	
	# Получаем текущие остатки для истории (используем API v4)
	cursor = ""
	while True:
		payload = {
			"filter": {
				"offer_id": products[:1000]
			},
			"limit": 1000,
			"cursor": cursor
		}
		try:
			resp = requests.post("https://api-seller.ozon.ru/v4/product/info/stocks", headers=headers, json=payload, timeout=60)
			if resp.status_code == 200:
				data = resp.json()
				for item in data.get("items", []):
					offer_id = item.get("offer_id")
					stocks = item.get("stocks", [])
					# Ищем остаток для типа fbs (склад продавца)
					for stock in stocks:
						if stock.get("type") == "fbs":
							current_stocks[offer_id] = stock.get("present", 0)
							break
				
				cursor = data.get("cursor", "")
				if not cursor:
					break
			else:
				print(f"[WARNING] API вернул статус {resp.status_code}")
				break
		except Exception as e:
			print(f"[WARNING] Не удалось получить текущие остатки: {e}")
			break
	
	# Собираем данные для истории
	history_items = []
	
	for i in range(0, len(products), 100):
		batch = products[i : i + 100]
		payload = {"stocks": [{"offer_id": oid, "stock": 0, "warehouse_id": OZON_WAREHOUSE_ID} for oid in batch]}
		max_attempts = 3
		for attempt in range(1, max_attempts + 1):
			try:
				r = requests.post("https://api-seller.ozon.ru/v2/products/stocks", headers=headers, json=payload, timeout=60)
				r.raise_for_status()
				break
			except requests.exceptions.RequestException:
				if attempt == max_attempts:
					raise
				import time as _t
				_t.sleep(2 * attempt)
		
		# Добавляем данные в историю
		for offer_id in batch:
			old_stock = current_stocks.get(offer_id, 0)
			history_items.append({
				"sku": offer_id,  # offer_id используется как SKU (артикул)
				"old_stock": old_stock,
				"new_stock": 0
			})
	
	print(f"Обнулено позиций: {len(products)}")
	
	# Сохраняем историю
	try:
		from modules.history import add_action
		add_action("reset", MARKETPLACE, SELLER_NAME, history_items)
		print(f"[OK] История сохранена: {len(history_items)} товаров")
	except Exception as e:
		print(f"[WARNING] Не удалось сохранить историю: {e}")


if __name__ == "__main__":
	main()

