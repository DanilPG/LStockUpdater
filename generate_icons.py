"""
Скрипт для генерации иконок PWA из исходного изображения.
Требует установки Pillow: pip install Pillow
"""
from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(size, output_path):
    """Создает иконку заданного размера."""
    # Создаем изображение с градиентом
    img = Image.new('RGB', (size, size), color='#1a1a2e')
    draw = ImageDraw.Draw(img)
    
    # Рисуем градиент
    for y in range(size):
        r = int(26 + (74 - 26) * y / size)
        g = int(26 + (144 - 26) * y / size)
        b = int(46 + (217 - 46) * y / size)
        draw.line([(0, y), (size, y)], fill=(r, g, b))
    
    # Рисуем иконку коробки
    box_size = size // 2
    box_x = (size - box_size) // 2
    box_y = (size - box_size) // 2
    
    # Коробка
    draw.rectangle([box_x, box_y, box_x + box_size, box_y + box_size], 
                   fill='#4a90d9', outline='#ffffff', width=max(2, size // 32))
    
    # Линия на коробке
    line_y = box_y + box_size // 3
    draw.line([(box_x, line_y), (box_x + box_size, line_y)], 
              fill='#ffffff', width=max(2, size // 32))
    
    # Сохраняем
    img.save(output_path, 'PNG')
    print(f"Создана иконка: {output_path} ({size}x{size})")

def main():
    """Генерирует все необходимые иконки."""
    sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    
    # Создаем директорию static, если её нет
    os.makedirs('static', exist_ok=True)
    
    print("Генерация иконок PWA...")
    for size in sizes:
        output_path = f'static/icon-{size}.png'
        create_icon(size, output_path)
    
    print("\n✅ Все иконки успешно созданы!")
    print("\nТеперь вы можете заменить их на свои, если хотите.")

if __name__ == '__main__':
    main()
