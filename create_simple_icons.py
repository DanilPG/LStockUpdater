"""
Простой скрипт для создания placeholder иконок PWA.
Не требует дополнительных зависимостей.
"""
import os

def create_placeholder_icon(size, output_path):
    """Создает простой placeholder для иконки."""
    # Создаем SVG иконку
    svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="{size}" height="{size}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{size}" height="{size}" fill="#1a1a2e"/>
  <rect x="{size//4}" y="{size//4}" width="{size//2}" height="{size//2}" fill="#4a90d9" stroke="#ffffff" stroke-width="{max(2, size//32)}"/>
  <line x1="{size//4}" y1="{size//4 + size//6}" x2="{size//4 + size//2}" y2="{size//4 + size//6}" stroke="#ffffff" stroke-width="{max(2, size//32)}"/>
</svg>'''
    
    # Сохраняем как SVG (можно конвертировать в PNG онлайн)
    with open(output_path.replace('.png', '.svg'), 'w') as f:
        f.write(svg_content)
    
    print(f"Создан placeholder: {output_path.replace('.png', '.svg')} ({size}x{size})")
    print(f"  Конвертируйте SVG в PNG на: https://convertio.co/ru/svg-png/")

def main():
    """Генерирует все необходимые placeholder иконки."""
    sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    
    # Создаем директорию static, если её нет
    os.makedirs('static', exist_ok=True)
    
    print("Генерация placeholder иконок PWA...")
    print("⚠️  Это SVG файлы. Конвертируйте их в PNG для использования в PWA.\n")
    
    for size in sizes:
        output_path = f'static/icon-{size}.png'
        create_placeholder_icon(size, output_path)
    
    print("\n✅ Все placeholder иконки созданы!")
    print("\n📝 Инструкция:")
    print("1. Откройте https://convertio.co/ru/svg-png/")
    print("2. Загрузите SVG файлы из папки static/")
    print("3. Скачайте PNG файлы")
    print("4. Замените SVG на PNG с теми же именами")
    print("\nИли используйте онлайн-генератор иконок:")
    print("https://realfavicongenerator.net/")

if __name__ == '__main__':
    main()
