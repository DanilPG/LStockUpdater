import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
from collections import defaultdict


def get_history_stats(days: int = 30) -> Dict[str, Any]:
    """
    Получает статистику из истории за указанный период
    
    Args:
        days: количество дней для анализа
    
    Returns:
        Словарь со статистикой
    """
    from .history import load_history
    
    history = load_history()
    cutoff_date = datetime.now() - timedelta(days=days)
    
    stats = {
        'total_updates': 0,
        'total_resets': 0,
        'by_marketplace': defaultdict(int),
        'by_seller': defaultdict(int),
        'by_date': defaultdict(lambda: {'updates': 0, 'resets': 0, 'items': 0}),
        'stock_changes': defaultdict(list),  # seller -> [(date, total_stock)]
        'items_processed': 0
    }
    
    for record in history:
        date_str = record.get('date', '')
        try:
            record_date = datetime.fromisoformat(date_str)
            if record_date < cutoff_date:
                continue
        except:
            continue
        
        action_type = record.get('action_type', '')
        marketplace = record.get('marketplace', '')
        seller = record.get('seller', '')
        items = record.get('items', [])
        
        date_key = record_date.strftime('%Y-%m-%d')
        
        if action_type == 'update':
            stats['total_updates'] += 1
            stats['by_date'][date_key]['updates'] += 1
        elif action_type == 'reset':
            stats['total_resets'] += 1
            stats['by_date'][date_key]['resets'] += 1
        
        stats['by_marketplace'][marketplace] += 1
        stats['by_seller'][seller] += 1
        stats['by_date'][date_key]['items'] += len(items)
        stats['items_processed'] += len(items)
        
        # Считаем общее количество товаров для графика
        total_stock = sum(item.get('new_stock', 0) for item in items)
        stats['stock_changes'][seller].append((record_date, total_stock))
    
    return stats


def get_top_products(days: int = 30, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Получает топ товаров с наибольшим количеством изменений
    
    Args:
        days: количество дней для анализа
        limit: количество товаров в топе
    
    Returns:
        Список товаров с статистикой
    """
    from .history import load_history
    
    history = load_history()
    cutoff_date = datetime.now() - timedelta(days=days)
    
    product_stats = defaultdict(lambda: {
        'sku': '',
        'changes': 0,
        'total_old': 0,
        'total_new': 0,
        'sellers': set()
    })
    
    for record in history:
        date_str = record.get('date', '')
        try:
            record_date = datetime.fromisoformat(date_str)
            if record_date < cutoff_date:
                continue
        except:
            continue
        
        seller = record.get('seller', '')
        items = record.get('items', [])
        
        for item in items:
            sku = item.get('sku', '')
            if sku:
                product_stats[sku]['sku'] = sku
                product_stats[sku]['changes'] += 1
                product_stats[sku]['total_old'] += item.get('old_stock', 0)
                product_stats[sku]['total_new'] += item.get('new_stock', 0)
                product_stats[sku]['sellers'].add(seller)
    
    # Сортируем по количеству изменений
    sorted_products = sorted(
        product_stats.values(),
        key=lambda x: x['changes'],
        reverse=True
    )
    
    # Преобразуем множества в списки для JSON
    for product in sorted_products[:limit]:
        product['sellers'] = list(product['sellers'])
    
    return sorted_products[:limit]


def get_daily_summary(days: int = 7) -> List[Dict[str, Any]]:
    """
    Получает ежедневную сводку за указанный период
    
    Args:
        days: количество дней
    
    Returns:
        Список ежедневных сводок
    """
    from .history import load_history
    
    history = load_history()
    cutoff_date = datetime.now() - timedelta(days=days)
    
    daily_data = defaultdict(lambda: {
        'date': '',
        'updates': 0,
        'resets': 0,
        'items_updated': 0,
        'marketplaces': set(),
        'sellers': set()
    })
    
    for record in history:
        date_str = record.get('date', '')
        try:
            record_date = datetime.fromisoformat(date_str)
            if record_date < cutoff_date:
                continue
        except:
            continue
        
        date_key = record_date.strftime('%Y-%m-%d')
        action_type = record.get('action_type', '')
        marketplace = record.get('marketplace', '')
        seller = record.get('seller', '')
        items = record.get('items', [])
        
        daily_data[date_key]['date'] = date_key
        
        if action_type == 'update':
            daily_data[date_key]['updates'] += 1
            daily_data[date_key]['items_updated'] += len(items)
        elif action_type == 'reset':
            daily_data[date_key]['resets'] += 1
        
        daily_data[date_key]['marketplaces'].add(marketplace)
        daily_data[date_key]['sellers'].add(seller)
    
    # Преобразуем в список и множества в списки
    result = []
    for date_key in sorted(daily_data.keys()):
        data = daily_data[date_key].copy()
        data['marketplaces'] = list(data['marketplaces'])
        data['sellers'] = list(data['sellers'])
        result.append(data)
    
    return result
