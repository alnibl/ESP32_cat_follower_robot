import cv2
import requests
import numpy as np
import time
from threading import Thread
import queue

class CatFollowerRobot:
    def __init__(self, camera_url, esp32_ip):
        """
        Инициализация робота-следователя за котом
        
        Args:
            camera_url: RTSP URL камеры (например, "rtsp://192.168.1.100:554/stream")
            esp32_ip: IP адрес ESP32 (например, "192.168.1.101")
        """
        self.camera_url = camera_url
        self.esp32_url = f"http://{esp32_ip}"
        self.cap = None
        self.running = False
        self.command_queue = queue.Queue()
        
        # Загрузка каскада Хаара для детекции котов
        # Можно также использовать YOLO или другие модели
        try:
            self.cat_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalcatface.xml')
        except:
            print("Warning: Cat cascade not found, using default face detector")
            self.cat_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Параметры управления
        self.frame_width = 640
        self.frame_height = 480
        self.center_threshold = 50  # Порог центрирования в пикселях
        self.min_area = 5000  # Минимальная площадь для детекции
        self.max_area = 100000  # Максимальная площадь (слишком близко)
        
    def connect_camera(self):
        """Подключение к IP камере через RTSP"""
        print(f"Connecting to camera: {self.camera_url}")
        self.cap = cv2.VideoCapture(self.camera_url)
        
        # Настройка параметров захвата
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Минимальный буфер для меньшей задержки
        
        if not self.cap.isOpened():
            raise Exception("Cannot connect to camera")
        
        print("Camera connected successfully")
        return True
    
    def send_command(self, action, speed=150):
        """Отправка команды на ESP32"""
        try:
            url = f"{self.esp32_url}/command"
            params = {"action": action, "speed": speed}
            response = requests.get(url, params=params, timeout=0.5)
            
            if response.status_code == 200:
                print(f"Command sent: {action} (speed: {speed})")
                return True
        except Exception as e:
            print(f"Error sending command: {e}")
        return False
    
    def command_sender_thread(self):
        """Поток для отправки команд с ограничением частоты"""
        last_command = None
        
        while self.running:
            try:
                # Получаем последнюю команду из очереди
                command = None
                while not self.command_queue.empty():
                    command = self.command_queue.get_nowait()
                
                if command and command != last_command:
                    action, speed = command
                    self.send_command(action, speed)
                    last_command = command
                
                time.sleep(0.1)  # Ограничение частоты команд
                
            except Exception as e:
                print(f"Command thread error: {e}")
    
    def detect_cat(self, frame):
        """
        Детекция кота в кадре
        Возвращает координаты и размер обнаруженного кота
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Детекция котов
        cats = self.cat_cascade.detectMultiScale(gray, 1.1, 4)
        
        if len(cats) > 0:
            # Выбираем самого большого кота (вероятно, ближайшего)
            largest_cat = max(cats, key=lambda x: x[2] * x[3])
            return largest_cat
        
        # Альтернативный метод - детекция по движению и цвету
        # (можно добавить для улучшения детекции)
        return None
    
    def calculate_movement(self, cat_rect, frame_center):
        """
        Расчет команды движения на основе положения кота
        
        Args:
            cat_rect: (x, y, w, h) - прямоугольник с котом
            frame_center: (cx, cy) - центр кадра
        
        Returns:
            (action, speed) - команда и скорость
        """
        if cat_rect is None:
            return ("stop", 0)
        
        x, y, w, h = cat_rect
        cat_center_x = x + w // 2
        cat_center_y = y + h // 2
        cat_area = w * h
        
        frame_center_x, frame_center_y = frame_center
        
        # Расчет отклонения от центра
        dx = cat_center_x - frame_center_x
        
        # Определение команды
        if cat_area < self.min_area:
            # Кот далеко - двигаемся вперед
            if abs(dx) > self.center_threshold:
                if dx > 0:
                    return ("right", 120)
                else:
                    return ("left", 120)
            else:
                return ("forward", 180)
                
        elif cat_area > self.max_area:
            # Кот слишком близко - отъезжаем
            return ("backward", 150)
            
        else:
            # Кот на оптимальном расстоянии
            if abs(dx) > self.center_threshold:
                # Поворачиваем к коту
                if dx > 0:
                    return ("right", 100)
                else:
                    return ("left", 100)
            else:
                # Кот в центре на хорошем расстоянии - стоим
                return ("stop", 0)
    
    def run(self):
        """Основной цикл работы робота"""
        if not self.connect_camera():
            return
        
        self.running = True
        
        # Запуск потока отправки команд
        command_thread = Thread(target=self.command_sender_thread)
        command_thread.start()
        
        frame_center = (self.frame_width // 2, self.frame_height // 2)
        
        print("Starting cat following mode...")
        print("Press 'q' to quit")
        
        try:
            while self.running:
                ret, frame = self.cap.read()
                if not ret:
                    print("Failed to get frame")
                    continue
                
                # Изменение размера для ускорения обработки
                frame = cv2.resize(frame, (self.frame_width, self.frame_height))
                
                # Детекция кота
                cat_rect = self.detect_cat(frame)
                
                # Расчет команды движения
                action, speed = self.calculate_movement(cat_rect, frame_center)
                
                # Добавление команды в очередь
                self.command_queue.put((action, speed))
                
                # Визуализация (опционально)
                if cat_rect is not None:
                    x, y, w, h = cat_rect
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(frame, f"Cat detected! Action: {action}", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                               0.7, (0, 255, 0), 2)
                else:
                    cv2.putText(frame, "Searching for cat...", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                               0.7, (0, 0, 255), 2)
                
                # Рисуем центр и пороги
                cv2.line(frame, (frame_center[0], 0), 
                        (frame_center[0], self.frame_height), (255, 0, 0), 1)
                cv2.line(frame, (frame_center[0] - self.center_threshold, 0),
                        (frame_center[0] - self.center_threshold, self.frame_height), 
                        (255, 255, 0), 1)
                cv2.line(frame, (frame_center[0] + self.center_threshold, 0),
                        (frame_center[0] + self.center_threshold, self.frame_height), 
                        (255, 255, 0), 1)
                
                cv2.imshow('Cat Follower Robot', frame)
                
                # Выход по нажатию 'q'
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        except KeyboardInterrupt:
            print("\nStopping robot...")
        finally:
            self.stop()
    
    def stop(self):
        """Остановка робота"""
        self.running = False
        self.send_command("stop", 0)
        
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        
        print("Robot stopped")

# Альтернативная версия с использованием YOLO для лучшей детекции
class CatFollowerRobotYOLO(CatFollowerRobot):
    def __init__(self, camera_url, esp32_ip, yolo_weights='yolov4.weights', 
                 yolo_config='yolov4.cfg', coco_names='coco.names'):
        super().__init__(camera_url, esp32_ip)
        
        # Загрузка YOLO
        try:
            self.net = cv2.dnn.readNet(yolo_weights, yolo_config)
            with open(coco_names, 'r') as f:
                self.classes = [line.strip() for line in f.readlines()]
            
            layer_names = self.net.getLayerNames()
            self.output_layers = [layer_names[i - 1] for i in self.net.getUnconnectedOutLayers()]
            
            print("YOLO loaded successfully")
            self.use_yolo = True
        except:
            print("YOLO not available, using cascade detector")
            self.use_yolo = False
    
    def detect_cat(self, frame):
        """Детекция кота с использованием YOLO"""
        if not self.use_yolo:
            return super().detect_cat(frame)
        
        height, width, _ = frame.shape
        
        # Подготовка изображения для YOLO
        blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
        self.net.setInput(blob)
        outputs = self.net.forward(self.output_layers)
        
        # Обработка результатов
        cats = []
        for output in outputs:
            for detection in output:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                
                # Проверяем, что это кот (class_id для кота в COCO)
                if confidence > 0.5 and self.classes[class_id] in ['cat', 'dog']:
                    # Координаты объекта
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)
                    
                    cats.append((x, y, w, h))
        
        if cats:
            # Возвращаем самого большого кота
            return max(cats, key=lambda x: x[2] * x[3])
        
        return None

if __name__ == "__main__":
    # Настройки подключения
    CAMERA_URL = "rtsp://192.168.1.100:554/stream"  # Замените на ваш RTSP URL
    ESP32_IP = "192.168.1.101"  # Замените на IP вашей ESP32
    
    # Создание и запуск робота
    robot = CatFollowerRobot(CAMERA_URL, ESP32_IP)
    
    # Или используйте версию с YOLO для лучшей детекции
    # robot = CatFollowerRobotYOLO(CAMERA_URL, ESP32_IP)
    
    robot.run()
