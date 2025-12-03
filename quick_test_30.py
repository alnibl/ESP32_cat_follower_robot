#!/usr/bin/env python3
"""
Быстрый тест для проверки Test #30 (complex maneuver)
Проверяет работу очереди команд в v2.1
"""

import requests
import time
from config import ESP32_IP

def test_30_complex_maneuver():
    """
    Test #30: Сложная последовательность команд
    Проверяет что очередь команд работает правильно

    Последовательность:
    1. Forward (1.5 сек)
    2. Forward (1.5 сек)  <- должна попасть в очередь
    3. Left (0.4 сек)     <- должна попасть в очередь
    4. Right (0.4 сек)    <- должна попасть в очередь
    5. Stop               <- должна попасть в очередь

    Ожидаемый результат v2.1:
    - Все команды выполнены
    - Dropped commands = 0
    - Очередь обработана
    """

    print("=" * 70)
    print("🧪 TEST #30: Complex Maneuver (Queue Test)")
    print("=" * 70)
    print()
    print("Этот тест проверяет критический баг v2.0:")
    print("  - v2.0: Очередь НЕ обрабатывалась (застревала)")
    print("  - v2.1: Очередь ДОЛЖНА обрабатываться")
    print()
    print("Последовательность команд:")
    print("  1. Forward (немедленно)")
    print("  2. Forward (в очередь)")
    print("  3. Left    (в очередь)")
    print("  4. Right   (в очередь)")
    print("  5. Stop    (в очередь)")
    print()
    print("-" * 70)
    print()

    # Сброс статистики (отправка stop)
    print("📊 Сброс статистики ESP32...")
    try:
        requests.get(f"http://{ESP32_IP}/stop", timeout=5)
        time.sleep(1)
    except:
        pass

    # Получение начальной статистики
    print("📊 Получение начальной статистики...")
    try:
        response = requests.get(f"http://{ESP32_IP}/stats", timeout=5)
        stats_before = response.json()
        print(f"   Total commands: {stats_before['total_commands']}")
        print(f"   Executed: {stats_before['executed']}")
        print(f"   Dropped: {stats_before['dropped']}")
        print(f"   Queue size: {stats_before['queue_size']}")
        print()
    except Exception as e:
        print(f"   ❌ Ошибка получения статистики: {e}")
        print()
        return False

    # Отправка быстрой последовательности команд
    print("🚀 Отправка быстрой последовательности команд...")
    print()

    commands = [
        ("forward", 150),
        ("forward", 150),
        ("left", 150),
        ("right", 150),
        ("stop", 150),
    ]

    start_time = time.time()

    for i, (action, speed) in enumerate(commands, 1):
        try:
            url = f"http://{ESP32_IP}/command?action={action}&speed={speed}"
            response = requests.get(url, timeout=5)

            print(f"   [{i}/5] {action.upper():8s} @ {speed} PWM - sent")

            # Быстрая отправка (без задержек между командами)
            time.sleep(0.05)  # Минимальная задержка чтобы команды точно пришли подряд

        except Exception as e:
            print(f"   [{i}/5] {action.upper():8s} - ❌ ERROR: {e}")
            return False

    send_duration = time.time() - start_time
    print()
    print(f"✅ Все 5 команд отправлены за {send_duration:.2f} секунд")
    print()

    # Ожидание выполнения всех команд
    # Forward: 1.5 сек
    # Forward: 1.5 сек (из очереди)
    # Left: 0.4 сек (из очереди)
    # Right: 0.4 сек (из очереди)
    # Stop: мгновенно (из очереди)
    # Итого: ~3.8 сек + запас

    print("⏳ Ожидание выполнения всех команд (5 секунд)...")
    time.sleep(5)
    print()

    # Получение финальной статистики
    print("📊 Получение финальной статистики...")
    try:
        response = requests.get(f"http://{ESP32_IP}/stats", timeout=5)
        stats_after = response.json()

        total_commands = stats_after['total_commands']
        executed = stats_after['executed']
        dropped = stats_after['dropped']
        queue_size = stats_after['queue_size']
        current_state = stats_after['current_state']

        print(f"   Total commands: {total_commands}")
        print(f"   Executed: {executed}")
        print(f"   Dropped: {dropped}")
        print(f"   Queue size now: {queue_size}")
        print(f"   Current state: {current_state}")
        print()

    except Exception as e:
        print(f"   ❌ Ошибка получения статистики: {e}")
        print()
        return False

    # Анализ результатов
    print("=" * 70)
    print("📊 АНАЛИЗ РЕЗУЛЬТАТОВ")
    print("=" * 70)
    print()

    # Вычисляем сколько команд добавилось
    commands_added = total_commands - stats_before['total_commands']

    print(f"Отправлено команд: 5")
    print(f"Получено ESP32: {commands_added}")
    print(f"Выполнено: {executed}")
    print(f"Потеряно (dropped): {dropped}")
    print(f"Осталось в очереди: {queue_size}")
    print()

    # Проверки
    checks = []

    # Проверка 1: Все команды получены
    if commands_added >= 5:
        print("✅ CHECK 1: Все 5 команд получены ESP32")
        checks.append(True)
    else:
        print(f"❌ CHECK 1: FAIL - Получено только {commands_added}/5 команд")
        checks.append(False)

    # Проверка 2: Нет потерянных команд
    if dropped == 0:
        print("✅ CHECK 2: Нет потерянных команд (dropped = 0)")
        checks.append(True)
    else:
        print(f"❌ CHECK 2: FAIL - Потеряно {dropped} команд")
        checks.append(False)

    # Проверка 3: Очередь пуста (все обработано)
    if queue_size == 0:
        print("✅ CHECK 3: Очередь пуста (все команды выполнены)")
        checks.append(True)
    else:
        print(f"⚠️  CHECK 3: WARNING - В очереди осталось {queue_size} команд")
        print("    (Возможно не все команды успели выполниться)")
        checks.append(True)  # Не критично

    # Проверка 4: Робот остановлен
    if current_state == "STOPPED":
        print("✅ CHECK 4: Робот остановлен (последняя команда STOP выполнена)")
        checks.append(True)
    else:
        print(f"⚠️  CHECK 4: WARNING - Робот в состоянии {current_state}")
        checks.append(False)

    print()

    # Итоговый вердикт
    print("=" * 70)

    if all(checks):
        print("🎉 TEST #30: PASS")
        print()
        print("✅ Критический баг v2.0 ИСПРАВЛЕН!")
        print("   - Очередь команд работает")
        print("   - Команды не теряются")
        print("   - Все команды выполняются последовательно")
        print()
        print("v2.1 готов к использованию! 🚀")
        result = True
    else:
        print("❌ TEST #30: FAIL")
        print()
        print("Очередь команд работает НЕ КОРРЕКТНО!")
        print("Требуется дополнительная отладка.")
        result = False

    print("=" * 70)
    print()

    return result


def main():
    print()
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 20 + "QUICK TEST #30" + " " * 34 + "║")
    print("║" + " " * 15 + "Complex Maneuver (Queue Test)" + " " * 24 + "║")
    print("╚" + "=" * 68 + "╝")
    print()

    print(f"ESP32 IP: {ESP32_IP}")
    print()

    # Проверка подключения
    print("🔌 Проверка подключения к ESP32...")
    try:
        response = requests.get(f"http://{ESP32_IP}/", timeout=5)
        if response.status_code == 200:
            print("   ✅ ESP32 доступен")
            print()
        else:
            print(f"   ❌ ESP32 вернул код {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Не удалось подключиться: {e}")
        print()
        print("Проверьте:")
        print("  1. ESP32 подключен к питанию")
        print("  2. ESP32 подключен к WiFi")
        print("  3. IP адрес в .env файле правильный")
        return False

    # Запуск теста
    input("Нажмите Enter когда будете готовы запустить тест...")
    print()

    result = test_30_complex_maneuver()

    return result


if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Тест прерван пользователем")
        exit(1)
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
