# Робот-следователь за котом - Инструкция по настройке

## Компоненты проекта
- IP камера с RTSP потоком
- ESP32-S3-DevkitC-1 N8R2
- Драйверы моторов MX1508 (2 штуки или 1 двухканальный)
- Платформа машинки с 2 моторами
- PowerBank или аккумулятор 18650 с повышающим преобразователем

## Схема подключения

### ESP32 -> MX1508 Driver
```
ESP32 GPIO12 -> MX1508 IN1 (Motor A Forward)
ESP32 GPIO14 -> MX1508 IN2 (Motor A Backward)
ESP32 GPIO27 -> MX1508 IN3 (Motor B Forward)
ESP32 GPIO26 -> MX1508 IN4 (Motor B Backward)
ESP32 GND    -> MX1508 GND
```

### Питание
```
PowerBank 5V -> MX1508 VIN (питание моторов)
PowerBank 5V -> ESP32 VIN или USB
PowerBank 5V -> IP Camera Power
Общий GND для всех компонентов
```

## Установка и настройка

### 1. Настройка ESP32

1. Установите Arduino IDE с поддержкой ESP32
2. Откройте файл `esp32_cat_follower.ino`
3. Измените параметры WiFi:
   ```cpp
   const char* ssid = "YOUR_WIFI_SSID";
   const char* password = "YOUR_WIFI_PASSWORD";
   ```
4. Загрузите код на ESP32
5. Откройте Serial Monitor (115200 baud) и запишите IP адрес ESP32

### 2. Настройка Python окружения на компьютере

```bash
# Создание виртуального окружения
python -m venv cat_follower_env

# Активация (Windows)
cat_follower_env\Scripts\activate

# Активация (Linux/Mac)
source cat_follower_env/bin/activate

# Установка зависимостей
pip install opencv-python
pip install opencv-contrib-python
pip install numpy
pip install requests
```

### 3. Настройка IP камеры

1. Подключите камеру к роутеру через приложение камеры
2. Найдите RTSP URL камеры (обычно в настройках приложения)
   Пример: `rtsp://admin:password@192.168.1.100:554/stream`

### 4. Запуск системы

1. Убедитесь, что все устройства подключены к одной WiFi сети
2. В файле `cat_follower_robot.py` измените параметры:
   ```python
   CAMERA_URL = "rtsp://192.168.1.100:554/stream"  # Ваш RTSP URL
   ESP32_IP = "192.168.1.101"  # IP адрес вашей ESP32
   ```
3. Запустите скрипт:
   ```bash
   python cat_follower_robot.py
   ```

## Решение проблемы с разными частотами WiFi

Роутер объединяет сети 2.4ГГц и 5ГГц в одну локальную сеть, поэтому:
- Компьютер на 5ГГц может общаться с ESP32 на 2.4ГГц
- Все устройства получают IP адреса из одной подсети (например, 192.168.1.x)
- Проверить связь можно командой ping:
  ```bash
  ping 192.168.1.101  # IP адрес ESP32
  ```

## Тестирование

### Тест ESP32 через браузер:
1. Откройте браузер
2. Перейдите на `http://[ESP32_IP]/`
3. Проверьте команды:
   - `http://[ESP32_IP]/forward`
   - `http://[ESP32_IP]/backward`
   - `http://[ESP32_IP]/left`
   - `http://[ESP32_IP]/right`
   - `http://[ESP32_IP]/stop`

### Тест Python скрипта:
```python
import requests

esp32_ip = "192.168.1.101"  # Ваш IP
url = f"http://{esp32_ip}/command"

# Тест движения вперед
response = requests.get(url, params={"action": "forward", "speed": 150})
print(response.json())
```

## Настройка параметров детекции

В файле `cat_follower_robot.py` можно настроить:

```python
self.center_threshold = 50   # Зона нечувствительности по X (пиксели)
self.min_area = 5000         # Минимальная площадь для начала движения
self.max_area = 100000       # Максимальная площадь (стоп при приближении)
```

## Улучшения детекции

### Вариант 1: Использование цвета
Добавьте детекцию по цвету шерсти кота в функцию `detect_cat()`

### Вариант 2: Использование YOLO
1. Скачайте веса YOLO:
   ```bash
   wget https://github.com/AlexeyAB/darknet/releases/download/darknet_yolo_v3_optimal/yolov4.weights
   wget https://raw.githubusercontent.com/AlexeyAB/darknet/master/cfg/yolov4.cfg
   wget https://raw.githubusercontent.com/AlexeyAB/darknet/master/data/coco.names
   ```
2. Используйте класс `CatFollowerRobotYOLO` вместо обычного

### Вариант 3: Использование движения
Добавьте детекцию движущихся объектов для поиска кота

## Отладка

### Если ESP32 не подключается к WiFi:
- Проверьте правильность SSID и пароля
- Убедитесь, что роутер работает на 2.4ГГц
- Проверьте, что в роутере не заблокированы новые устройства

### Если нет видео с камеры:
- Проверьте RTSP URL в VLC плеере
- Убедитесь, что компьютер и камера в одной сети
- Попробуйте уменьшить разрешение потока в настройках камеры

### Если моторы не работают:
- Проверьте подключение проводов
- Измерьте напряжение на выходах MX1508
- Проверьте достаточность тока от PowerBank

## Механическая сборка

1. Закрепите камеру на передней части платформы
2. ESP32 разместите в защищенном месте
3. Драйверы моторов закрепите рядом с моторами
4. PowerBank разместите по центру для баланса
5. Обеспечьте надежное крепление всех проводов

## Дополнительные функции

### Автономный режим (без компьютера)
Можно портировать алгоритм детекции прямо на ESP32-CAM

### Управление с телефона
Добавьте веб-интерфейс с видео трансляцией

### Запись маршрута
Сохраняйте путь следования для анализа поведения кота

### Ночное видение
Добавьте ИК подсветку для работы в темноте
