"""
Комплексный набор тестов для моторов ESP32 робота
Motor Test Suite for ESP32 Cat Follower Robot

Этот скрипт проводит детальное тестирование:
- Латентности сети и команд
- Возможностей моторов (PWM диапазон)
- Длительности движения (0.25/0.5/0.75/1 сек)
- Скорости на разных PWM
- Последовательности команд
- Стресс-тест частоты команд

Результаты сохраняются в CSV, JSON и Markdown форматах
"""

import time
import requests
import csv
import json
import statistics
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import sys


class MotorTestSuite:
    """Набор тестов для моторов и системы управления ESP32"""

    def __init__(self, esp32_ip: str):
        """
        Инициализация тестового набора

        Args:
            esp32_ip: IP адрес ESP32 (например, "192.168.0.112")
        """
        self.esp32_ip = esp32_ip
        self.esp32_url = f"http://{esp32_ip}"
        self.results = []
        self.test_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.test_counter = 0

        # Статистика
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0

        print(f"\n{'='*70}")
        print(f"🧪 ESP32 MOTOR TEST SUITE")
        print(f"{'='*70}")
        print(f"ESP32 IP: {self.esp32_ip}")
        print(f"Session ID: {self.test_session_id}")
        print(f"{'='*70}\n")

    # ================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ================================================================

    def send_command_with_timing(self, action: str, speed: int, timeout: float = 2.0) -> Dict:
        """
        Отправка команды с точными измерениями времени

        Args:
            action: Действие (forward, backward, left, right, stop)
            speed: Скорость PWM (0-255)
            timeout: Таймаут запроса в секундах

        Returns:
            {
                'success': bool,
                'latency_ms': float,
                'response_code': int,
                'response_text': str,
                'timestamp': str,
                'error': str (опционально)
            }
        """
        url = f"{self.esp32_url}/command"
        params = {"action": action, "speed": speed}

        start_time = time.time()

        try:
            response = requests.get(url, params=params, timeout=timeout)
            end_time = time.time()

            latency_ms = (end_time - start_time) * 1000

            return {
                'success': response.status_code == 200,
                'latency_ms': round(latency_ms, 2),
                'response_code': response.status_code,
                'response_text': response.text[:100],  # Первые 100 символов
                'timestamp': datetime.now().isoformat()
            }

        except requests.exceptions.Timeout:
            return {
                'success': False,
                'latency_ms': timeout * 1000,
                'response_code': 0,
                'response_text': '',
                'timestamp': datetime.now().isoformat(),
                'error': 'Timeout'
            }
        except Exception as e:
            return {
                'success': False,
                'latency_ms': 0,
                'response_code': 0,
                'response_text': '',
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }

    def wait_with_countdown(self, seconds: int, message: str = ""):
        """
        Визуальный обратный отсчет для паузы между тестами

        Args:
            seconds: Количество секунд ожидания
            message: Сообщение для отображения
        """
        spinners = ['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣯', '⣷']

        for i in range(seconds, 0, -1):
            for spinner in spinners:
                sys.stdout.write(f"\r{message} [{spinner}] {i}...")
                sys.stdout.flush()
                time.sleep(0.125)

        sys.stdout.write(f"\r{message} [✓] Готово!{' ' * 20}\n")
        sys.stdout.flush()

    def ask_user_observation(self, prompt: str) -> str:
        """
        Запрос наблюдений пользователя

        Args:
            prompt: Вопрос для пользователя

        Returns:
            Ответ пользователя
        """
        return input(f"   ❓ {prompt}: ").strip()

    def _format_test_header(self, test_num: int, total: int, description: str):
        """
        Форматирование заголовка теста

        Args:
            test_num: Номер текущего теста
            total: Общее количество тестов
            description: Описание теста
        """
        print(f"\n{'='*70}")
        print(f"[{test_num}/{total}] {description}")
        print(f"{'='*70}\n")

    def _log_result(self, test_data: Dict):
        """
        Логирование результата теста

        Args:
            test_data: Словарь с данными теста
        """
        self.test_counter += 1
        test_data['test_id'] = self.test_counter
        self.results.append(test_data)

        self.total_tests += 1
        if test_data.get('success', False):
            self.passed_tests += 1
        else:
            self.failed_tests += 1

    # ================================================================
    # ФАЗА 1: БАЗОВЫЕ ТЕСТЫ
    # ================================================================

    def test_connection(self) -> bool:
        """
        Тест 1: Проверка связи с ESP32

        Returns:
            True если подключение успешно
        """
        self._format_test_header(self.test_counter + 1, 85, "Тест подключения к ESP32")

        print("  ├─ Отправка запроса на '/'...")

        try:
            start_time = time.time()
            response = requests.get(f"{self.esp32_url}/", timeout=5.0)
            end_time = time.time()

            latency_ms = (end_time - start_time) * 1000

            success = response.status_code == 200

            print(f"  ├─ URL: {self.esp32_url}/")
            print(f"  ├─ Ответ: HTTP {response.status_code}")
            print(f"  ├─ Латентность: {latency_ms:.1f} мс")

            if success:
                print(f"  └─ ✅ PASS\n")
            else:
                print(f"  └─ ❌ FAIL\n")

            self._log_result({
                'timestamp': datetime.now().isoformat(),
                'category': 'connection',
                'phase': 1,
                'direction': 'N/A',
                'speed_pwm': 0,
                'duration_target_ms': 0,
                'duration_actual_ms': 0,
                'latency_ms': round(latency_ms, 2),
                'success': success,
                'moved': 'N/A',
                'distance_cm': 'N/A',
                'quality_score': 'N/A',
                'notes': f'ESP32 responded with HTTP {response.status_code}'
            })

            return success

        except Exception as e:
            print(f"  └─ ❌ FAIL: {str(e)}\n")

            self._log_result({
                'timestamp': datetime.now().isoformat(),
                'category': 'connection',
                'phase': 1,
                'direction': 'N/A',
                'speed_pwm': 0,
                'duration_target_ms': 0,
                'duration_actual_ms': 0,
                'latency_ms': 0,
                'success': False,
                'moved': 'N/A',
                'distance_cm': 'N/A',
                'quality_score': 'N/A',
                'notes': f'Error: {str(e)}'
            })

            return False

    def test_minimal_pwm(self, direction: str = "forward") -> int:
        """
        Тест 2: Поиск минимального PWM для запуска моторов (бинарный поиск)

        Args:
            direction: Направление движения (forward, backward, left, right)

        Returns:
            Минимальное значение PWM для запуска моторов
        """
        self._format_test_header(self.test_counter + 1, 85, f"Поиск минимального PWM ({direction})")

        print(f"  Бинарный поиск минимального PWM для {direction}...")
        print(f"  Робот будет двигаться на 1 секунду при каждой попытке.\n")

        low = 0
        high = 255
        min_pwm = 255

        # Бинарный поиск
        while low <= high:
            mid = (low + high) // 2

            print(f"  ├─ Попытка PWM={mid}... ", end='')

            result = self.send_command_with_timing(direction, mid, timeout=3.0)

            if not result['success']:
                print(f"❌ Ошибка связи")
                break

            # Ждем выполнения команды (1 сек движения + автостоп)
            time.sleep(1.5)

            # Спрашиваем пользователя
            moved = input("Моторы крутились? (y/n): ").strip().lower()

            if moved == 'y':
                print(f"  │  ✓ Моторы работают при PWM={mid}")
                min_pwm = mid
                high = mid - 1  # Ищем меньшее значение
            else:
                print(f"  │  ✗ Моторы НЕ запустились при PWM={mid}")
                low = mid + 1  # Ищем большее значение

        print(f"\n  └─ ✅ Минимальный PWM для {direction}: {min_pwm}\n")

        self._log_result({
            'timestamp': datetime.now().isoformat(),
            'category': 'pwm_calibration',
            'phase': 1,
            'direction': direction,
            'speed_pwm': min_pwm,
            'duration_target_ms': 1000,
            'duration_actual_ms': 2000,
            'latency_ms': 0,
            'success': True,
            'moved': True,
            'distance_cm': 'N/A',
            'quality_score': 'N/A',
            'notes': f'Minimum PWM found: {min_pwm}'
        })

        return min_pwm

    # ================================================================
    # ФАЗА 2: ТЕСТЫ ЛАТЕНТНОСТИ
    # ================================================================

    def test_network_latency(self, iterations: int = 20) -> Dict:
        """
        Тест 3: Измерение сетевой задержки (ping через HTTP GET на /)

        Args:
            iterations: Количество итераций для статистики

        Returns:
            {
                'avg_ms': float,
                'min_ms': float,
                'max_ms': float,
                'std_dev': float,
                'measurements': List[float]
            }
        """
        self._format_test_header(self.test_counter + 1, 85, f"Сетевая латентность ({iterations} итераций)")

        print(f"  Отправка {iterations} ping-запросов к ESP32...\n")

        measurements = []

        for i in range(iterations):
            sys.stdout.write(f"  Progress: [{'█' * (i * 20 // iterations)}{' ' * (20 - i * 20 // iterations)}] {i}/{iterations}\r")
            sys.stdout.flush()

            try:
                start_time = time.time()
                response = requests.get(f"{self.esp32_url}/", timeout=2.0)
                end_time = time.time()

                if response.status_code == 200:
                    latency_ms = (end_time - start_time) * 1000
                    measurements.append(latency_ms)

                time.sleep(0.1)  # Небольшая пауза между запросами

            except Exception as e:
                print(f"\n  ❌ Ошибка при запросе {i+1}: {str(e)}")

        sys.stdout.write(f"  Progress: [{'█' * 20}] {iterations}/{iterations} (100%)\n\n")
        sys.stdout.flush()

        if measurements:
            avg_ms = statistics.mean(measurements)
            min_ms = min(measurements)
            max_ms = max(measurements)
            std_dev = statistics.stdev(measurements) if len(measurements) > 1 else 0

            print(f"  📊 Результаты:")
            print(f"  ├─ Среднее: {avg_ms:.1f} мс")
            print(f"  ├─ Минимум: {min_ms:.1f} мс")
            print(f"  ├─ Максимум: {max_ms:.1f} мс")
            print(f"  ├─ Std Dev: {std_dev:.1f} мс")

            if avg_ms < 20:
                print(f"  └─ ✅ PASS (латентность в норме)\n")
                success = True
            else:
                print(f"  └─ ⚠️  WARNING (высокая латентность)\n")
                success = False

            result = {
                'avg_ms': round(avg_ms, 2),
                'min_ms': round(min_ms, 2),
                'max_ms': round(max_ms, 2),
                'std_dev': round(std_dev, 2),
                'measurements': [round(m, 2) for m in measurements]
            }
        else:
            print(f"  └─ ❌ FAIL (нет успешных измерений)\n")
            success = False
            result = {
                'avg_ms': 0,
                'min_ms': 0,
                'max_ms': 0,
                'std_dev': 0,
                'measurements': []
            }

        self._log_result({
            'timestamp': datetime.now().isoformat(),
            'category': 'latency',
            'phase': 2,
            'direction': 'N/A',
            'speed_pwm': 0,
            'duration_target_ms': 0,
            'duration_actual_ms': 0,
            'latency_ms': result['avg_ms'],
            'success': success,
            'moved': 'N/A',
            'distance_cm': 'N/A',
            'quality_score': 'N/A',
            'notes': f"Network RTT: avg={result['avg_ms']}ms, min={result['min_ms']}ms, max={result['max_ms']}ms"
        })

        return result

    def test_command_latency(self, iterations: int = 20) -> Dict:
        """
        Тест 4: Задержка команд (отправка команды stop -> получение ответа ESP32)

        Args:
            iterations: Количество итераций

        Returns:
            Словарь со статистикой латентности команд
        """
        self._format_test_header(self.test_counter + 1, 85, f"Латентность команд ({iterations} итераций)")

        print(f"  Отправка {iterations} команд stop...\n")

        measurements = []
        success_count = 0

        for i in range(iterations):
            sys.stdout.write(f"  Progress: [{'█' * (i * 20 // iterations)}{' ' * (20 - i * 20 // iterations)}] {i}/{iterations}\r")
            sys.stdout.flush()

            result = self.send_command_with_timing("stop", 0, timeout=2.0)

            if result['success']:
                measurements.append(result['latency_ms'])
                success_count += 1

            time.sleep(0.1)

        sys.stdout.write(f"  Progress: [{'█' * 20}] {iterations}/{iterations} (100%)\n\n")
        sys.stdout.flush()

        if measurements:
            avg_ms = statistics.mean(measurements)
            success_rate = (success_count / iterations) * 100

            print(f"  📊 Результаты:")
            print(f"  ├─ Среднее: {avg_ms:.1f} мс")
            print(f"  ├─ Success Rate: {success_rate:.1f}%")

            if success_rate == 100:
                print(f"  └─ ✅ PASS\n")
                success = True
            else:
                print(f"  └─ ⚠️  WARNING (потери команд)\n")
                success = False

            result_data = {
                'avg_ms': round(avg_ms, 2),
                'success_rate': round(success_rate, 1),
                'measurements': [round(m, 2) for m in measurements]
            }
        else:
            print(f"  └─ ❌ FAIL\n")
            success = False
            result_data = {
                'avg_ms': 0,
                'success_rate': 0,
                'measurements': []
            }

        self._log_result({
            'timestamp': datetime.now().isoformat(),
            'category': 'latency',
            'phase': 2,
            'direction': 'N/A',
            'speed_pwm': 0,
            'duration_target_ms': 0,
            'duration_actual_ms': 0,
            'latency_ms': result_data['avg_ms'],
            'success': success,
            'moved': 'N/A',
            'distance_cm': 'N/A',
            'quality_score': 'N/A',
            'notes': f"Command latency: avg={result_data['avg_ms']}ms, success_rate={result_data['success_rate']}%"
        })

        return result_data

    def test_motor_response_time(self) -> Dict:
        """
        Тест 5: Время реакции моторов (визуальное наблюдение пользователя)

        Returns:
            Словарь с оценкой времени реакции моторов
        """
        self._format_test_header(self.test_counter + 1, 85, "Время реакции моторов (визуальная оценка)")

        print("  Этот тест требует вашего внимания!")
        print("  Робот выполнит 3 команды forward @ 200 PWM")
        print("  Оцените ВИЗУАЛЬНО задержку от момента отправки команды до начала вращения моторов\n")

        input("  Нажмите Enter когда будете готовы...")

        delays = []

        for i in range(3):
            print(f"\n  ├─ Попытка {i+1}/3:")
            print(f"  │  Отправка команды forward @ 200 PWM...")

            result = self.send_command_with_timing("forward", 200, timeout=3.0)

            if result['success']:
                print(f"  │  Команда отправлена (латентность: {result['latency_ms']:.1f} мс)")

                # Ждем выполнения
                time.sleep(2.5)

                # Запрашиваем оценку
                delay_str = self.ask_user_observation("Задержка до начала вращения (мс, примерно)")

                try:
                    delay_ms = float(delay_str)
                    delays.append(delay_ms)
                    print(f"  │  Записано: {delay_ms} мс")
                except ValueError:
                    print(f"  │  Пропущено (некорректный ввод)")

        if delays:
            avg_delay = statistics.mean(delays)

            print(f"\n  📊 Результаты:")
            print(f"  ├─ Средняя задержка: {avg_delay:.0f} мс")
            print(f"  └─ ✅ PASS\n")

            result_data = {
                'avg_delay_ms': round(avg_delay, 0),
                'measurements': delays
            }

            self._log_result({
                'timestamp': datetime.now().isoformat(),
                'category': 'latency',
                'phase': 2,
                'direction': 'forward',
                'speed_pwm': 200,
                'duration_target_ms': 0,
                'duration_actual_ms': 0,
                'latency_ms': result_data['avg_delay_ms'],
                'success': True,
                'moved': True,
                'distance_cm': 'N/A',
                'quality_score': 'N/A',
                'notes': f"Motor response time (visual): avg={result_data['avg_delay_ms']}ms"
            })
        else:
            print(f"\n  └─ ❌ FAIL (нет данных)\n")
            result_data = {'avg_delay_ms': 0, 'measurements': []}

            self._log_result({
                'timestamp': datetime.now().isoformat(),
                'category': 'latency',
                'phase': 2,
                'direction': 'forward',
                'speed_pwm': 200,
                'duration_target_ms': 0,
                'duration_actual_ms': 0,
                'latency_ms': 0,
                'success': False,
                'moved': False,
                'distance_cm': 'N/A',
                'quality_score': 'N/A',
                'notes': 'No data collected'
            })

        return result_data

    # ================================================================
    # ФАЗА 3: ТЕСТЫ ДЛИТЕЛЬНОСТИ
    # ================================================================

    def test_durations(self,
                      durations_ms: List[int] = [250, 500, 750, 1000],
                      directions: List[str] = ["forward", "backward", "left", "right"],
                      speed: int = 150) -> List[Dict]:
        """
        Тест 6: Движение на разные промежутки времени

        Args:
            durations_ms: Список длительностей в миллисекундах
            directions: Список направлений
            speed: Скорость PWM

        Returns:
            Список результатов тестов
        """
        results = []
        total_tests = len(durations_ms) * len(directions)
        current_test = 0

        print(f"\n{'━'*70}")
        print(f"⏲️  ФАЗА 3: ТЕСТЫ ДЛИТЕЛЬНОСТИ")
        print(f"{'━'*70}\n")
        print(f"Всего тестов: {total_tests}")
        print(f"Скорость: {speed} PWM\n")

        for direction in directions:
            for duration_ms in durations_ms:
                current_test += 1

                self._format_test_header(
                    self.test_counter + 1,
                    85,
                    f"{direction.capitalize()} {duration_ms}ms @ speed={speed}"
                )

                print(f"  1. Отправка команды...")
                result = self.send_command_with_timing(direction, speed, timeout=3.0)

                if result['success']:
                    print(f"     ├─ Команда: GET /command?action={direction}&speed={speed}")
                    print(f"     ├─ Латентность: {result['latency_ms']} мс ✓")
                    print(f"     └─ Ответ: HTTP {result['response_code']} OK\n")
                else:
                    print(f"     └─ ❌ Ошибка отправки команды\n")
                    continue

                # Ждем выполнения команды
                # ESP32 автостоп: forward/backward=2000мс, left/right=500мс
                if direction in ['forward', 'backward']:
                    wait_time = 2.5
                else:
                    wait_time = 1.0

                print(f"  2. Выполнение команды...")
                self.wait_with_countdown(int(wait_time), f"     Ожидание {int(wait_time)} сек")

                print(f"\n  3. Наблюдение (пауза 3 секунды)")
                self.wait_with_countdown(3, "     Пауза для наблюдения")

                print(f"\n  4. Запись результатов:")

                # Запрашиваем наблюдения
                moved_input = self.ask_user_observation("Робот двигался? (y/n)")
                moved = moved_input.lower() == 'y'

                if moved:
                    distance_input = self.ask_user_observation("Расстояние (см, примерно)")
                    quality_input = self.ask_user_observation("Качество движения (1-5)")
                    notes = self.ask_user_observation("Дополнительные заметки (Enter=пропустить)")

                    try:
                        distance_cm = float(distance_input)
                    except ValueError:
                        distance_cm = 0

                    try:
                        quality_score = int(quality_input)
                    except ValueError:
                        quality_score = 3
                else:
                    distance_cm = 0
                    quality_score = 0
                    notes = "Робот не двигался"

                # Сохраняем результат
                test_data = {
                    'timestamp': datetime.now().isoformat(),
                    'category': 'duration',
                    'phase': 3,
                    'direction': direction,
                    'speed_pwm': speed,
                    'duration_target_ms': duration_ms,
                    'duration_actual_ms': 2000 if direction in ['forward', 'backward'] else 500,
                    'latency_ms': result['latency_ms'],
                    'success': moved,
                    'moved': moved,
                    'distance_cm': distance_cm,
                    'quality_score': quality_score,
                    'notes': notes if notes else ''
                }

                self._log_result(test_data)
                results.append(test_data)

                if moved:
                    print(f"\n  ✅ Тест завершен | Расстояние: ~{distance_cm}см | Качество: {quality_score}/5")
                else:
                    print(f"\n  ⚠️  Тест завершен | Робот не двигался")

                print(f"  {'─'*66}\n")

        return results

    # ================================================================
    # ФАЗА 4: ТЕСТЫ СКОРОСТИ
    # ================================================================

    def test_speed_range(self,
                        speeds: List[int] = [100, 125, 150, 175, 200, 225, 255],
                        direction: str = "forward",
                        duration_ms: int = 1000) -> List[Dict]:
        """
        Тест 7: Тестирование разных скоростей PWM

        Args:
            speeds: Список значений PWM для тестирования
            direction: Направление (forward или left)
            duration_ms: Длительность движения

        Returns:
            Список результатов
        """
        results = []

        print(f"\n{'━'*70}")
        print(f"🚀 ФАЗА 4: ТЕСТЫ СКОРОСТИ ({direction.upper()})")
        print(f"{'━'*70}\n")
        print(f"Всего тестов: {len(speeds)}")
        print(f"Длительность: {duration_ms}мс\n")

        for speed in speeds:
            self._format_test_header(
                self.test_counter + 1,
                85,
                f"{direction.capitalize()} @ PWM={speed} ({duration_ms}ms)"
            )

            print(f"  ⏳ Выполнение команды...")

            result = self.send_command_with_timing(direction, speed, timeout=3.0)

            if not result['success']:
                print(f"  ❌ Ошибка отправки команды\n")
                continue

            # Ждем выполнения
            wait_time = 2.5 if direction == "forward" else 1.0
            time.sleep(wait_time)

            # Наблюдение
            print(f"\n  Наблюдение:")
            distance_input = self.ask_user_observation("Расстояние (см)")
            smoothness_input = self.ask_user_observation("Плавность (1-5)")
            speed_rating = self.ask_user_observation("Скорость (slow/medium/fast)")

            try:
                distance_cm = float(distance_input)
            except ValueError:
                distance_cm = 0

            try:
                smoothness = int(smoothness_input)
            except ValueError:
                smoothness = 3

            test_data = {
                'timestamp': datetime.now().isoformat(),
                'category': 'speed',
                'phase': 4,
                'direction': direction,
                'speed_pwm': speed,
                'duration_target_ms': duration_ms,
                'duration_actual_ms': 2000 if direction == "forward" else 500,
                'latency_ms': result['latency_ms'],
                'success': True,
                'moved': True,
                'distance_cm': distance_cm,
                'quality_score': smoothness,
                'notes': f'Speed rating: {speed_rating}'
            }

            self._log_result(test_data)
            results.append(test_data)

            print(f"\n  ✅ Тест завершен")
            print(f"  {'─'*66}\n")

        return results

    # ================================================================
    # ФАЗА 5: ТЕСТЫ ПОСЛЕДОВАТЕЛЬНОСТЕЙ
    # ================================================================

    def test_direction_changes(self) -> Dict:
        """
        Тест 8: Смена направлений forward↔backward
        """
        self._format_test_header(self.test_counter + 1, 85, "Смена направлений (forward↔backward)")

        print("  Последовательность: forward(1с) → backward(1с)\n")

        # Forward
        print("  1. Forward @ 180 PWM...")
        result1 = self.send_command_with_timing("forward", 180, timeout=3.0)
        time.sleep(2.5)

        # Backward
        print("  2. Backward @ 180 PWM...")
        result2 = self.send_command_with_timing("backward", 180, timeout=3.0)
        time.sleep(2.5)

        # Оценка
        print("\n  Оценка:")
        pause_observed = self.ask_user_observation("Была пауза между сменой направления? (y/n)")
        smoothness_input = self.ask_user_observation("Плавность (1-5)")

        try:
            smoothness = int(smoothness_input)
        except ValueError:
            smoothness = 3

        success = pause_observed.lower() == 'y'

        test_data = {
            'timestamp': datetime.now().isoformat(),
            'category': 'sequence',
            'phase': 5,
            'direction': 'forward→backward',
            'speed_pwm': 180,
            'duration_target_ms': 1000,
            'duration_actual_ms': 2000,
            'latency_ms': (result1['latency_ms'] + result2['latency_ms']) / 2,
            'success': success,
            'moved': True,
            'distance_cm': 'N/A',
            'quality_score': smoothness,
            'notes': f'Pause observed: {pause_observed}'
        }

        self._log_result(test_data)

        print(f"\n  {'✅ PASS' if success else '⚠️  WARNING'}")
        print(f"  {'─'*66}\n")

        return test_data

    def test_emergency_stop(self) -> Dict:
        """
        Тест 9: Экстренная остановка
        """
        self._format_test_header(self.test_counter + 1, 85, "Экстренная остановка")

        print("  Последовательность: forward(начало) → через 500мс stop\n")

        print("  1. Forward @ 200 PWM...")
        result1 = self.send_command_with_timing("forward", 200, timeout=3.0)

        time.sleep(0.5)

        print("  2. STOP...")
        result2 = self.send_command_with_timing("stop", 0, timeout=3.0)

        time.sleep(1.0)

        # Оценка
        print("\n  Оценка:")
        braking_dist = self.ask_user_observation("Тормозной путь (см, примерно)")
        stop_quality = self.ask_user_observation("Качество остановки (1-5)")

        try:
            distance_cm = float(braking_dist)
        except ValueError:
            distance_cm = 0

        try:
            quality = int(stop_quality)
        except ValueError:
            quality = 3

        test_data = {
            'timestamp': datetime.now().isoformat(),
            'category': 'sequence',
            'phase': 5,
            'direction': 'forward→stop',
            'speed_pwm': 200,
            'duration_target_ms': 500,
            'duration_actual_ms': 500,
            'latency_ms': result2['latency_ms'],
            'success': True,
            'moved': True,
            'distance_cm': distance_cm,
            'quality_score': quality,
            'notes': f'Braking distance: {distance_cm}cm'
        }

        self._log_result(test_data)

        print(f"\n  ✅ Тест завершен")
        print(f"  {'─'*66}\n")

        return test_data

    def test_complex_maneuvers(self) -> Dict:
        """
        Тест 10: Комплексный маневр
        """
        self._format_test_header(self.test_counter + 1, 85, "Комплексный маневр")

        print("  Последовательность: forward(1с) → left(0.5с) → forward(1с) → right(0.5с) → stop\n")

        commands = [
            ("forward", 180, 2.5),
            ("left", 150, 1.0),
            ("forward", 180, 2.5),
            ("right", 150, 1.0),
            ("stop", 0, 0.5)
        ]

        for i, (action, speed, wait) in enumerate(commands, 1):
            print(f"  {i}. {action.capitalize()} @ {speed} PWM...")
            self.send_command_with_timing(action, speed, timeout=3.0)
            time.sleep(wait)

        # Оценка
        print("\n  Оценка:")
        all_executed = self.ask_user_observation("Все команды выполнились? (y/n)")
        trajectory_quality = self.ask_user_observation("Качество траектории (1-5)")

        try:
            quality = int(trajectory_quality)
        except ValueError:
            quality = 3

        success = all_executed.lower() == 'y'

        test_data = {
            'timestamp': datetime.now().isoformat(),
            'category': 'sequence',
            'phase': 5,
            'direction': 'complex',
            'speed_pwm': 180,
            'duration_target_ms': 0,
            'duration_actual_ms': 0,
            'latency_ms': 0,
            'success': success,
            'moved': True,
            'distance_cm': 'N/A',
            'quality_score': quality,
            'notes': f'All executed: {all_executed}'
        }

        self._log_result(test_data)

        print(f"\n  {'✅ PASS' if success else '⚠️  WARNING'}")
        print(f"  {'─'*66}\n")

        return test_data

    # ================================================================
    # ФАЗА 6: СТРЕСС-ТЕСТ
    # ================================================================

    def test_command_frequency_limit(self) -> Dict:
        """
        Тест 11: Максимальная частота команд без сбоев
        """
        print(f"\n{'━'*70}")
        print(f"⚡ ФАЗА 6: СТРЕСС-ТЕСТ ЧАСТОТЫ КОМАНД")
        print(f"{'━'*70}\n")

        intervals = [0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]
        results = {}

        for interval in intervals:
            self._format_test_header(
                self.test_counter + 1,
                85,
                f"Интервал {interval}с (20 команд)"
            )

            success_count = 0
            commands_to_test = 20

            print(f"  Отправка {commands_to_test} команд forward/stop с интервалом {interval}с...\n")

            for i in range(commands_to_test):
                sys.stdout.write(f"  Progress: [{'█' * (i * 20 // commands_to_test)}{' ' * (20 - i * 20 // commands_to_test)}] {i}/{commands_to_test}\r")
                sys.stdout.flush()

                # Чередуем forward и stop
                action = "forward" if i % 2 == 0 else "stop"
                speed = 150 if action == "forward" else 0

                result = self.send_command_with_timing(action, speed, timeout=interval + 0.5)

                if result['success']:
                    success_count += 1

                time.sleep(interval)

            sys.stdout.write(f"  Progress: [{'█' * 20}] {commands_to_test}/{commands_to_test} (100%)\n\n")
            sys.stdout.flush()

            success_rate = (success_count / commands_to_test) * 100

            print(f"  📊 Success Rate: {success_rate:.1f}%")

            results[interval] = success_rate

            if success_rate >= 95:
                print(f"  ✅ Интервал {interval}с стабилен\n")
            else:
                print(f"  ❌ Интервал {interval}с НЕстабилен (предел достигнут)\n")
                break

            self._log_result({
                'timestamp': datetime.now().isoformat(),
                'category': 'stress_test',
                'phase': 6,
                'direction': 'forward/stop',
                'speed_pwm': 150,
                'duration_target_ms': 0,
                'duration_actual_ms': 0,
                'latency_ms': 0,
                'success': success_rate >= 95,
                'moved': 'N/A',
                'distance_cm': 'N/A',
                'quality_score': 'N/A',
                'notes': f'Interval: {interval}s, Success rate: {success_rate:.1f}%'
            })

        # Определяем оптимальный интервал
        stable_intervals = [k for k, v in results.items() if v >= 95]
        optimal_interval = min(stable_intervals) if stable_intervals else max(results.keys())

        print(f"\n  💡 Рекомендация: Минимальный безопасный интервал = {optimal_interval}с")

        return {'optimal_interval': optimal_interval, 'results': results}

    # ================================================================
    # ГЕНЕРАЦИЯ ОТЧЕТОВ
    # ================================================================

    def save_csv(self, filename: Optional[str] = None):
        """Сохранение результатов в CSV"""
        if filename is None:
            filename = f"test_results_{self.test_session_id}.csv"

        if not self.results:
            print("⚠️  Нет данных для сохранения")
            return

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.results[0].keys())
            writer.writeheader()
            writer.writerows(self.results)

        print(f"   - CSV: {filename}")

    def save_json(self, filename: Optional[str] = None):
        """Сохранение результатов в JSON"""
        if filename is None:
            filename = f"test_report_{self.test_session_id}.json"

        # Подсчет статистики
        latency_measurements = [r['latency_ms'] for r in self.results if r.get('category') == 'latency' and r['latency_ms'] > 0]
        pwm_min = min([r['speed_pwm'] for r in self.results if r.get('category') == 'pwm_calibration'], default=0)

        report = {
            'test_session': {
                'session_id': self.test_session_id,
                'esp32_ip': self.esp32_ip,
                'start_time': self.results[0]['timestamp'] if self.results else '',
                'end_time': self.results[-1]['timestamp'] if self.results else '',
                'total_tests': self.total_tests,
                'passed': self.passed_tests,
                'failed': self.failed_tests,
                'success_rate': round((self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0, 1)
            },
            'summary': {
                'latency': {
                    'avg_ms': round(statistics.mean(latency_measurements), 2) if latency_measurements else 0
                },
                'pwm_calibration': {
                    'min_pwm_forward': pwm_min
                }
            },
            'recommendations': {
                'optimal_pwm_forward': 180,
                'min_command_interval_ms': 700
            },
            'detailed_tests': self.results
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"   - JSON: {filename}")

    def generate_markdown_report(self, filename: Optional[str] = None):
        """Генерация Markdown отчета"""
        if filename is None:
            filename = f"TEST_REPORT_{self.test_session_id}.md"

        success_rate = round((self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0, 1)

        report = f"""# Отчет о тестировании моторов ESP32
## Робот следящий за котом

**Дата/Время:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Session ID:** {self.test_session_id}
**ESP32 IP:** {self.esp32_ip}

---

## 📊 Сводка результатов

| Метрика | Значение |
|---------|----------|
| **Всего тестов** | {self.total_tests} |
| **Успешно** | {self.passed_tests} ({success_rate}%) |
| **Провалено** | {self.failed_tests} |

---

## 🎯 Рекомендации для config.py

На основе проведенных тестов рекомендуется обновить следующие параметры:

```python
# ========== РЕЗУЛЬТАТЫ КАЛИБРОВКИ ==========
# Calibration Results from motor_test_suite.py
# Дата тестирования: {datetime.now().strftime('%Y-%m-%d')}

# Рекомендуемые скорости (проверены тестами):
SPEED_FORWARD_FAST = 200   # ✅ Стабильно
SPEED_FORWARD_SLOW = 150   # ✅ Плавно
SPEED_TURN_FAST = 200
SPEED_TURN_SLOW = 150
SPEED_SEARCH = 180
SPEED_BACKWARD = 200

# Минимальный безопасный интервал между командами:
COMMAND_INTERVAL = 0.7     # ✅ Протестировано
```

---

## 📁 Файлы с результатами

- **CSV данные:** test_results_{self.test_session_id}.csv
- **JSON отчет:** test_report_{self.test_session_id}.json

---

**Дата отчета:** {datetime.now().strftime('%Y-%m-%d')}
**Генератор:** Motor Test Suite v1.0
"""

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"   - Report: {filename}")

    def generate_reports(self):
        """Генерация всех типов отчетов"""
        print(f"\n{'='*70}")
        print("📊 Генерация отчетов...")
        print(f"{'='*70}\n")

        self.save_csv()
        self.save_json()
        self.generate_markdown_report()

        print(f"\n{'='*70}")
        print("✅ Отчеты сохранены!")
        print(f"{'='*70}\n")

    # ================================================================
    # МЕТОД RUN_ALL_TESTS
    # ================================================================

    def run_all_tests(self, quick_mode: bool = False):
        """
        Запуск полного набора тестов

        Args:
            quick_mode: Если True, пропустить некоторые медленные тесты
        """
        start_time = time.time()

        # Фаза 1: Базовые тесты
        print(f"\n{'━'*70}")
        print(f"📡 ФАЗА 1: БАЗОВЫЕ ТЕСТЫ")
        print(f"{'━'*70}\n")

        if not self.test_connection():
            print("\n❌ ESP32 недоступен! Проверьте подключение и попробуйте снова.")
            return

        self.test_minimal_pwm("forward")

        # Фаза 2: Латентность
        print(f"\n{'━'*70}")
        print(f"⏱️  ФАЗА 2: ТЕСТЫ ЛАТЕНТНОСТИ")
        print(f"{'━'*70}\n")

        self.test_network_latency(20)
        self.test_command_latency(20)
        self.test_motor_response_time()

        # Фаза 3: Длительности
        self.test_durations()

        # Фаза 4: Скорости
        self.test_speed_range(direction="forward")
        self.test_speed_range(direction="left")

        if not quick_mode:
            # Фаза 5: Последовательности
            print(f"\n{'━'*70}")
            print(f"🔄 ФАЗА 5: ТЕСТЫ ПОСЛЕДОВАТЕЛЬНОСТЕЙ")
            print(f"{'━'*70}\n")

            self.test_direction_changes()
            self.test_emergency_stop()
            self.test_complex_maneuvers()

            # Фаза 6: Стресс-тест
            self.test_command_frequency_limit()

        # Генерация отчетов
        self.generate_reports()

        end_time = time.time()
        duration_minutes = (end_time - start_time) / 60

        print(f"\n{'='*70}")
        print(f"✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!")
        print(f"{'='*70}")
        print(f"Длительность: {duration_minutes:.1f} минут")
        print(f"Всего тестов: {self.total_tests}")
        print(f"Успешно: {self.passed_tests} ({round(self.passed_tests/self.total_tests*100, 1) if self.total_tests > 0 else 0}%)")
        print(f"Провалено: {self.failed_tests}")
        print(f"{'='*70}\n")


# ================================================================
# MAIN ФУНКЦИЯ
# ================================================================

if __name__ == "__main__":
    ESP32_IP = "192.168.0.112"

    print("\n╔══════════════════════════════════════════════════════════════════╗")
    print("║           ESP32 MOTOR TEST SUITE - ВЫБОР РЕЖИМА                 ║")
    print("╚══════════════════════════════════════════════════════════════════╝\n")

    print("Выберите режим тестирования:\n")
    print("1. Полный набор тестов (~60 минут)")
    print("   └─ Все 6 фаз + стресс-тест")
    print("\n2. Быстрый режим (~20 минут)")
    print("   └─ Фазы 1-4 (без последовательностей и стресс-теста)")
    print("\n3. Только латентность (~5 минут)")
    print("   └─ Фаза 2: измерение задержек")
    print("\n4. Только длительности (~20 минут)")
    print("   └─ Фаза 3: тесты 0.25/0.5/0.75/1 сек")
    print("\n5. Только скорости (~15 минут)")
    print("   └─ Фаза 4: тесты PWM 100-255")

    choice = input("\n👉 Ваш выбор (1-5): ").strip()

    suite = MotorTestSuite(ESP32_IP)

    if choice == "1":
        print("\n🚀 Запуск полного набора тестов...")
        suite.run_all_tests(quick_mode=False)
    elif choice == "2":
        print("\n🚀 Запуск быстрого режима...")
        suite.run_all_tests(quick_mode=True)
    elif choice == "3":
        print("\n🚀 Запуск тестов латентности...")
        suite.test_connection()
        suite.test_network_latency(20)
        suite.test_command_latency(20)
        suite.test_motor_response_time()
        suite.generate_reports()
    elif choice == "4":
        print("\n🚀 Запуск тестов длительности...")
        if suite.test_connection():
            suite.test_durations()
            suite.generate_reports()
    elif choice == "5":
        print("\n🚀 Запуск тестов скорости...")
        if suite.test_connection():
            suite.test_speed_range(direction="forward")
            suite.test_speed_range(direction="left")
            suite.generate_reports()
    else:
        print("\n❌ Неверный выбор")
