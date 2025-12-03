#!/usr/bin/env python3
"""
Скрипт для мониторинга статистики ESP32 через WiFi
Работает БЕЗ USB кабеля - только через WiFi!

Использование:
    python monitor_stats.py
"""

import requests
import time
import sys
from datetime import datetime

ESP32_IP = "192.168.0.112"
STATS_URL = f"http://{ESP32_IP}/stats"
REFRESH_INTERVAL = 2  # Обновлять каждые 2 секунды

def clear_screen():
    """Очистка экрана (работает в Windows)"""
    import os
    os.system('cls' if os.name == 'nt' else 'clear')

def fetch_stats():
    """Получить статистику через WiFi"""
    try:
        response = requests.get(STATS_URL, timeout=2.0)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except requests.exceptions.RequestException as e:
        return None

def print_stats(stats):
    """Красиво напечатать статистику"""
    if not stats:
        print("❌ Не удалось получить статистику!")
        print(f"   Проверьте что ESP32 подключен к WiFi")
        print(f"   IP адрес: {ESP32_IP}")
        return

    total = stats.get('total_commands', 0)
    executed = stats.get('executed', 0)
    dropped = stats.get('dropped', 0)
    queue_size = stats.get('queue_size', 0)
    current_state = stats.get('current_state', 'UNKNOWN')
    waiting = stats.get('waiting_for_change', False)
    auto_stop = stats.get('auto_stop_enabled', False)

    # Вычисляем производные метрики
    queued = total - executed - dropped if total > 0 else 0
    drop_rate = (dropped / total * 100) if total > 0 else 0.0
    success_rate = (executed / total * 100) if total > 0 else 0.0

    # Заголовок
    print("=" * 60)
    print(f"  ESP32 Cat Robot v2.1 - Live Statistics Monitor")
    print(f"  Time: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)
    print()

    # Основная статистика
    print(f"📊 Commands Statistics:")
    print(f"  ├─ Total received:      {total}")
    print(f"  ├─ Executed:            {executed} ({success_rate:.1f}%)")
    print(f"  ├─ In queue now:        {queue_size}/5")

    # Dropped commands с цветовой индикацией
    if dropped == 0:
        print(f"  └─ Dropped:             {dropped} ✅")
    else:
        print(f"  └─ Dropped:             {dropped} ❌ ({drop_rate:.1f}%)")

    print()

    # Состояние мотора
    state_emoji = {
        'STOPPED': '⏹️',
        'FORWARD': '▶️',
        'BACKWARD': '⏪',
        'LEFT': '⬅️',
        'RIGHT': '➡️'
    }
    emoji = state_emoji.get(current_state, '❓')

    print(f"🤖 Motor State:")
    print(f"  ├─ Current:             {emoji} {current_state}")
    print(f"  ├─ Auto-stop enabled:   {'🟢 YES' if auto_stop else '⚪ NO'}")
    print(f"  └─ Direction change:    {'🟡 WAITING' if waiting else '⚪ READY'}")

    print()
    print("=" * 60)
    print(f"Обновление каждые {REFRESH_INTERVAL} сек. Нажмите Ctrl+C для выхода.")
    print()

def main():
    """Главная функция мониторинга"""
    print("\n🚀 Запуск мониторинга ESP32 через WiFi...")
    print(f"📡 IP адрес: {ESP32_IP}")
    print(f"🔄 Интервал обновления: {REFRESH_INTERVAL} сек")
    print("\nПроверка подключения...")

    # Первая проверка
    stats = fetch_stats()
    if not stats:
        print("\n❌ ОШИБКА: Не удалось подключиться к ESP32!")
        print(f"\nПроверьте:")
        print(f"  1. ESP32 включен и подключен к WiFi")
        print(f"  2. IP адрес правильный: {ESP32_IP}")
        print(f"  3. Откройте в браузере: http://{ESP32_IP}/")
        print(f"  4. Если IP другой - измените в скрипте (строка 13)")
        sys.exit(1)

    print("✅ Подключение успешно!\n")
    time.sleep(1)

    try:
        while True:
            clear_screen()
            stats = fetch_stats()
            print_stats(stats)
            time.sleep(REFRESH_INTERVAL)
    except KeyboardInterrupt:
        print("\n\n👋 Мониторинг остановлен. До свидания!")
        sys.exit(0)

if __name__ == "__main__":
    main()
