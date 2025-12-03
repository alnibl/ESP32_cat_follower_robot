"""
Робот следящий за котом с использованием YOLO11
Cat Follower Robot with YOLO11 Detection
"""

import cv2
import requests
import numpy as np
import time
import random
from ultralytics import YOLO
import config

class CatFollowerYOLO11:
    def __init__(self, camera_url=None, esp32_ip=None):
        """
        Инициализация робота-следователя за котом

        Args:
            camera_url: RTSP URL камеры (если None - берётся из config.py)
            esp32_ip: IP адрес ESP32 (если None - берётся из config.py)
        """
        # Параметры подключения
        self.camera_url = camera_url or config.CAMERA_URL
        self.esp32_ip = esp32_ip or config.ESP32_IP
        self.esp32_url = f"http://{self.esp32_ip}"

        # Загрузка модели YOLO11
        print(f"Загрузка модели YOLO: {config.YOLO_MODEL}")
        self.model = YOLO(config.YOLO_MODEL)
        print("Модель YOLO11 загружена успешно!")

        # Параметры видео
        self.frame_width = config.FRAME_WIDTH
        self.frame_height = config.FRAME_HEIGHT
        self.show_video = config.SHOW_VIDEO

        # Параметры детекции
        self.confidence_threshold = config.CONFIDENCE_THRESHOLD
        self.cat_class_id = config.CAT_CLASS_ID

        # Параметры управления
        self.center_threshold = config.CENTER_THRESHOLD
        self.min_distance = config.MIN_DISTANCE
        self.max_distance = config.MAX_DISTANCE

        # Скорости
        self.speed_forward_fast = config.SPEED_FORWARD_FAST
        self.speed_forward_slow = config.SPEED_FORWARD_SLOW
        self.speed_turn_fast = config.SPEED_TURN_FAST
        self.speed_turn_slow = config.SPEED_TURN_SLOW
        self.speed_search = config.SPEED_SEARCH
        self.speed_backward = config.SPEED_BACKWARD

        # Калибровка
        self.drift_compensation = config.DRIFT_COMPENSATION
        self.drift_correction_frequency = config.DRIFT_CORRECTION_FREQUENCY
        self.drift_counter = 0

        # Временные параметры
        self.command_interval = config.COMMAND_INTERVAL
        self.last_command_time = 0
        self.last_command = None

        # Режим поиска
        self.search_change_interval = config.SEARCH_CHANGE_INTERVAL
        self.last_search_change = time.time()
        self.search_direction = "right"

        # Отладка
        self.debug = config.DEBUG
        self.show_fps = config.SHOW_FPS
        self.show_center_lines = config.SHOW_CENTER_LINES

        # FPS counter
        self.fps_start_time = time.time()
        self.fps_frame_count = 0
        self.current_fps = 0

        # Видеопоток
        self.cap = None

        # Счётчик кадров для пропуска
        self.frame_skip = config.FRAME_SKIP if hasattr(config, 'FRAME_SKIP') else 1
        self.frame_counter = 0

    def connect_camera(self):
        """Подключение к IP камере через RTSP"""
        print(f"\nПодключение к камере: {self.camera_url}")
        self.cap = cv2.VideoCapture(self.camera_url)

        if not self.cap.isOpened():
            print("❌ Ошибка: Не удалось подключиться к камере!")
            print("Проверьте:")
            print(f"  1. URL камеры в config.py: {self.camera_url}")
            print("  2. Камера включена и доступна в сети")
            print("  3. RTSP порт открыт (обычно 554)")
            return False

        # Настройка параметров захвата
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Минимальный буфер для меньшей задержки

        print("✅ Камера подключена успешно!")
        return True

    def detect_cat(self, frame):
        """
        Детекция кота с использованием YOLO11

        Args:
            frame: кадр изображения

        Returns:
            (x, y, w, h, confidence) или None если кот не найден
        """
        # Запуск детекции YOLO
        results = self.model.predict(frame, conf=self.confidence_threshold, verbose=False)

        # Поиск котов в результатах
        cats = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])

                # Проверяем что это кот (class_id == 15 в COCO)
                if class_id == self.cat_class_id and confidence >= self.confidence_threshold:
                    # Получаем координаты bbox
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    x = int(x1)
                    y = int(y1)
                    w = int(x2 - x1)
                    h = int(y2 - y1)

                    cats.append((x, y, w, h, confidence))

        if cats:
            # Возвращаем самого большого кота (вероятно, ближайшего)
            largest_cat = max(cats, key=lambda c: c[2] * c[3])
            if self.debug:
                print(f"🐱 Кот детектирован! Размер bbox: {largest_cat[2]}x{largest_cat[3]}, уверенность: {largest_cat[4]:.2f}")
            return largest_cat

        return None

    def calculate_movement(self, cat_bbox, frame_center):
        """
        Расчет команды движения на основе положения кота

        Args:
            cat_bbox: (x, y, w, h, confidence) или None
            frame_center: (cx, cy) - центр кадра

        Returns:
            (action, speed, duration) - команда, скорость и длительность
        """
        # Если кота нет → режим поиска
        if cat_bbox is None:
            return self.search_mode()

        x, y, w, h, confidence = cat_bbox
        cat_center_x = x + w // 2
        cat_size = h  # Высота bbox как индикатор расстояния

        frame_center_x, frame_center_y = frame_center

        # Отклонение от центра кадра
        dx = cat_center_x - frame_center_x

        # ========== ЛОГИКА ПРИОРИТЕТОВ ==========

        # 1. Кот слишком близко (высота bbox > MAX_DISTANCE)
        if cat_size > self.max_distance:
            if self.debug:
                print(f"⬅️  Кот слишком близко (размер {cat_size}px > {self.max_distance}px) - отъезжаем назад")
            return ("backward", self.speed_backward, config.MOVE_DURATION)

        # 2. Кот далеко (высота bbox < MIN_DISTANCE)
        elif cat_size < self.min_distance:
            # Если кот НЕ в центре - сначала центрируем
            if abs(dx) > self.center_threshold:
                direction = "right" if dx > 0 else "left"
                if self.debug:
                    print(f"🔄 Кот далеко и сбоку (отклонение {dx}px) - поворот {direction}")
                return (direction, self.speed_turn_slow, config.TURN_DURATION)
            # Кот в центре - едем вперёд
            else:
                if self.debug:
                    print(f"⬆️  Кот далеко но в центре - едем вперёд быстро")
                return ("forward", self.speed_forward_fast, config.MOVE_DURATION)

        # 3. Кот на оптимальном расстоянии (MIN_DISTANCE - MAX_DISTANCE)
        else:
            # Если кот сбоку - поворачиваем
            if abs(dx) > self.center_threshold:
                direction = "right" if dx > 0 else "left"
                # Скорость зависит от отклонения (пропорциональное управление)
                speed = min(self.speed_turn_fast, self.speed_turn_slow + abs(dx) // 2)
                if self.debug:
                    print(f"↔️  Кот на оптимальном расстоянии но сбоку (отклонение {dx}px) - поворот {direction}")
                return (direction, speed, config.TURN_DURATION)
            # Кот в центре на хорошем расстоянии - стоим
            else:
                if self.debug:
                    print(f"✅ Кот в центре на оптимальном расстоянии - СТОП")
                return ("stop", 0, 0)

    def search_mode(self):
        """
        Режим поиска кота - поворот с паузами для сканирования

        Returns:
            (action, speed, duration)
        """
        current_time = time.time()

        # Каждые SEARCH_CHANGE_INTERVAL секунд меняем направление
        if current_time - self.last_search_change > self.search_change_interval:
            if config.SEARCH_DIRECTION == "random":
                self.search_direction = random.choice(["left", "right"])
            else:
                self.search_direction = config.SEARCH_DIRECTION

            self.last_search_change = current_time
            if self.debug:
                print(f"🔍 Режим поиска: смена направления на {self.search_direction}")

        # Алгоритм с паузами: Поворот → Пауза для сканирования → Поворот → ...
        # Цикл 3 секунды: 0.35сек поворот → 2.65сек пауза (сканирование)
        cycle_time = current_time % 3  # 0-3 секунды циклически

        if cycle_time < 0.35:
            # Поворот 350мс (в 2 раза меньше чем было 700мс)
            if self.debug:
                print(f"🔍 Поиск: поворот {self.search_direction}")
            return (self.search_direction, self.speed_search, config.TURN_DURATION)
        else:
            # Пауза 2.65 секунды - сканируем (в 2 раза больше чем было 1.3сек)
            if self.debug:
                print(f"👀 Поиск: пауза (сканирование кадров)")
            return ("stop", 0, 100)

    def apply_drift_compensation(self, action, speed):
        """
        Компенсация ухода влево при движении вперёд

        Args:
            action: команда движения
            speed: скорость

        Returns:
            (action, speed) - скорректированные команда и скорость
        """
        if action == "forward" and self.drift_compensation > 0:
            # Чередуем команды: forward → mini-right → forward
            self.drift_counter += 1
            if self.drift_counter % self.drift_correction_frequency == 0:
                if self.debug:
                    print(f"🔧 Компенсация дрейфа: лёгкий поворот вправо")
                # Возвращаем только action и speed (duration не нужен здесь)
                return ("right", int(speed * self.drift_compensation))

        return (action, speed)

    def send_command(self, action, speed=150):
        """
        Отправка команды на ESP32

        Args:
            action: действие (forward, backward, left, right, stop)
            speed: скорость (0-255)

        Returns:
            True если команда отправлена успешно
        """
        try:
            url = f"{self.esp32_url}/command"
            params = {"action": action, "speed": speed}
            response = requests.get(url, params=params, timeout=0.5)

            if response.status_code == 200:
                if self.debug:
                    print(f"📡 Команда отправлена: {action} (скорость: {speed})")
                return True
            else:
                print(f"⚠️  Ошибка ответа ESP32: {response.status_code}")
                return False

        except requests.exceptions.Timeout:
            print(f"⏱️  Таймаут при отправке команды {action}")
            return False
        except requests.exceptions.ConnectionError:
            print(f"❌ Ошибка подключения к ESP32 ({self.esp32_url})")
            return False
        except Exception as e:
            print(f"❌ Ошибка отправки команды: {e}")
            return False

    def draw_debug_info(self, frame, cat_bbox, action, speed):
        """
        Отрисовка отладочной информации на кадре

        Args:
            frame: кадр изображения
            cat_bbox: координаты кота или None
            action: текущая команда
            speed: текущая скорость
        """
        frame_center_x = frame.shape[1] // 2
        frame_center_y = frame.shape[0] // 2

        # Рисуем центральные линии
        if self.show_center_lines:
            # Вертикальная линия центра
            cv2.line(frame, (frame_center_x, 0), (frame_center_x, frame.shape[0]), (255, 0, 0), 2)

            # Линии зоны центрирования
            cv2.line(frame, (frame_center_x - self.center_threshold, 0),
                    (frame_center_x - self.center_threshold, frame.shape[0]),
                    (255, 255, 0), 1)
            cv2.line(frame, (frame_center_x + self.center_threshold, 0),
                    (frame_center_x + self.center_threshold, frame.shape[0]),
                    (255, 255, 0), 1)

        # Рисуем bbox кота
        if cat_bbox is not None:
            x, y, w, h, confidence = cat_bbox

            # Цвет bbox зависит от расстояния
            if h > self.max_distance:
                color = (0, 0, 255)  # Красный - слишком близко
                distance_text = "TOO CLOSE"
            elif h < self.min_distance:
                color = (255, 255, 0)  # Жёлтый - далеко
                distance_text = "FAR"
            else:
                color = (0, 255, 0)  # Зелёный - оптимально
                distance_text = "OPTIMAL"

            # Рисуем прямоугольник
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)

            # Центр кота
            cat_center_x = x + w // 2
            cat_center_y = y + h // 2
            cv2.circle(frame, (cat_center_x, cat_center_y), 5, color, -1)

            # Линия от центра кадра до центра кота
            cv2.line(frame, (frame_center_x, frame_center_y),
                    (cat_center_x, cat_center_y), color, 2)

            # Текст с информацией
            cv2.putText(frame, f"Cat detected! ({distance_text})",
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            cv2.putText(frame, f"Size: {h}px | Conf: {confidence:.2f}",
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        else:
            # Кот не детектирован
            cv2.putText(frame, "Searching for cat...",
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # Текущая команда
        cv2.putText(frame, f"Action: {action.upper()} (speed: {speed})",
                   (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # FPS
        if self.show_fps:
            cv2.putText(frame, f"FPS: {self.current_fps:.1f}",
                       (frame.shape[1] - 120, 30), cv2.FONT_HERSHEY_SIMPLEX,
                       0.6, (0, 255, 0), 2)

    def update_fps(self):
        """Обновление счётчика FPS"""
        self.fps_frame_count += 1
        elapsed_time = time.time() - self.fps_start_time

        if elapsed_time > 1.0:  # Обновляем каждую секунду
            self.current_fps = self.fps_frame_count / elapsed_time
            self.fps_frame_count = 0
            self.fps_start_time = time.time()

    def run(self):
        """Главный цикл работы робота"""
        # Подключение к камере
        if not self.connect_camera():
            return

        print("\n" + "="*50)
        print("🤖 Робот следящий за котом запущен!")
        print("="*50)
        print(f"📹 Камера: {self.camera_url}")
        print(f"🎛️  ESP32: {self.esp32_url}")
        print(f"🧠 Модель: {config.YOLO_MODEL}")
        print("\n⌨️  Нажмите 'q' для выхода")
        print("="*50 + "\n")

        try:
            while True:
                # Захват кадра
                ret, frame = self.cap.read()
                if not ret:
                    print("⚠️  Ошибка чтения кадра с камеры")
                    time.sleep(0.1)
                    continue

                # Изменение размера для ускорения
                frame = cv2.resize(frame, (self.frame_width, self.frame_height))

                # Пропуск кадров для стабильности
                self.frame_counter += 1
                if self.frame_counter % self.frame_skip != 0:
                    # Показываем кадр, но не обрабатываем
                    if self.show_video:
                        cv2.putText(frame, "Skipped frame", (10, 120),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (128, 128, 128), 2)
                        cv2.imshow('Cat Follower Robot - YOLO11', frame)
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            break
                    continue

                # Детекция кота (только на каждом N-ом кадре)
                cat_bbox = self.detect_cat(frame)

                # Расчёт команды движения
                frame_center = (frame.shape[1] // 2, frame.shape[0] // 2)
                action, speed, duration = self.calculate_movement(cat_bbox, frame_center)

                # Применение компенсации дрейфа
                action, speed = self.apply_drift_compensation(action, speed)

                # Отправка команды (не чаще чем раз в COMMAND_INTERVAL)
                current_time = time.time()

                # ВАЖНО: Если кот детектирован - отправляем команду сразу (игнорируем интервал)
                # Иначе только если прошёл интервал
                should_send = False
                if cat_bbox is not None:
                    # Кот найден - отправляем команду немедленно для быстрой реакции
                    should_send = True
                elif current_time - self.last_command_time > self.command_interval:
                    # Кота нет - отправляем по таймеру (режим поиска)
                    should_send = True

                if should_send:
                    self.send_command(action, speed)
                    self.last_command = (action, speed)
                    self.last_command_time = current_time

                # Обновление FPS
                self.update_fps()

                # Визуализация
                if self.show_video:
                    self.draw_debug_info(frame, cat_bbox, action, speed)
                    cv2.imshow('Cat Follower Robot - YOLO11', frame)

                    # Выход по нажатию 'q'
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        print("\n👋 Выход из программы...")
                        break

        except KeyboardInterrupt:
            print("\n\n⏹️  Остановка робота (Ctrl+C)...")
        finally:
            self.stop()

    def test_detection_only(self):
        """Тестовый режим - только детекция без управления моторами"""
        if not self.connect_camera():
            return

        print("\n" + "="*50)
        print("🧪 ТЕСТОВЫЙ РЕЖИМ: Только детекция (без управления)")
        print("="*50)
        print("⌨️  Нажмите 'q' для выхода\n")

        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    continue

                frame = cv2.resize(frame, (self.frame_width, self.frame_height))
                cat_bbox = self.detect_cat(frame)

                self.update_fps()
                self.draw_debug_info(frame, cat_bbox, "TEST_MODE", 0)

                cv2.imshow('Cat Detection Test - YOLO11', frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        except KeyboardInterrupt:
            print("\n👋 Выход из тестового режима...")
        finally:
            self.stop()

    def stop(self):
        """Остановка робота и освобождение ресурсов"""
        print("\n🛑 Остановка робота...")

        # Остановка моторов
        self.send_command("stop", 0)

        # Освобождение камеры
        if self.cap:
            self.cap.release()

        # Закрытие окон
        cv2.destroyAllWindows()

        print("✅ Робот остановлен. До свидания!\n")


if __name__ == "__main__":
    # Создание робота
    robot = CatFollowerYOLO11()

    # Запуск в рабочем режиме
    robot.run()

    # Или запуск в тестовом режиме (только детекция):
    # robot.test_detection_only()
