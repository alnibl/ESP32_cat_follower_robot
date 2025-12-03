# Настройка Arduino IDE для ESP32-S3-DevKitC-1 N8R2

## Шаг 1: Установка Arduino IDE

1. Скачайте последнюю версию Arduino IDE (2.x) с официального сайта: https://www.arduino.cc/en/software
2. Установите Arduino IDE

## Шаг 2: Добавление поддержки ESP32

1. Откройте Arduino IDE
2. Перейдите в **File** → **Preferences** (или **Ctrl+Comma**)
3. В поле **Additional Boards Manager URLs** добавьте:
   ```
   https://espressif.github.io/arduino-esp32/package_esp32_index.json
   ```
4. Если там уже есть другие URL, добавьте через запятую или новую строку
5. Нажмите **OK**

## Шаг 3: Установка платформы ESP32

1. Перейдите в **Tools** → **Board** → **Boards Manager**
2. В поисковой строке введите: `esp32`
3. Найдите **"esp32 by Espressif Systems"**
4. Нажмите **Install** (установите последнюю версию, например 3.x.x)
5. Дождитесь завершения установки (может занять несколько минут)

## Шаг 4: Выбор платы ESP32-S3

1. Перейдите в **Tools** → **Board** → **esp32** → **ESP32S3 Dev Module**
2. Настройте параметры платы:

### Критически важные настройки для вашей платы:

- **Board**: ESP32S3 Dev Module
- **USB CDC On Boot**: Enabled (ВАЖНО!)
- **USB DFU On Boot**: Disabled
- **Upload Mode**: UART0 / Hardware CDC
- **USB Mode**: Hardware CDC and JTAG
- **PSRAM**: OPI PSRAM (у вас N8R2 - это 8MB PSRAM)
- **Flash Mode**: QIO 80MHz
- **Flash Size**: 8MB (вы имеете N8R2 = 8MB Flash)
- **Partition Scheme**: 8M with spiffs (3.6MB APP/1.5MB SPIFFS)
- **Core Debug Level**: None (или Info для отладки)
- **Erase All Flash Before Sketch Upload**: Disabled
- **Upload Speed**: 921600 (можно попробовать 115200 если будут проблемы)

## Шаг 5: Подключение платы к компьютеру

1. Возьмите USB-C кабель (обязательно с поддержкой передачи данных!)
2. Подключите ESP32-S3 к компьютеру через **любой из двух USB-C разъемов**
   - Один разъем: USB (Native USB)
   - Второй разъем: COM (UART)
   - Рекомендую начать с разъема с надписью "USB"

3. Windows должна автоматически определить устройство
4. Проверьте, что драйвера установлены:
   - Откройте **Device Manager** (Диспетчер устройств)
   - Найдите раздел **Ports (COM & LPT)**
   - Должен появиться порт типа **"USB Serial Device (COMx)"** или **"Silicon Labs CP210x USB to UART Bridge (COMx)"**

## Шаг 6: Выбор COM порта

1. В Arduino IDE перейдите в **Tools** → **Port**
2. Выберите порт с вашей ESP32 (обычно самый большой номер COM)
   - Если не уверены, отключите USB, посмотрите какие порты есть
   - Затем подключите USB и посмотрите какой порт добавился

## Шаг 7: Тестовая загрузка (Blink)

Перед загрузкой вашего основного кода, проверим работу:

```cpp
void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
}

void loop() {
  digitalWrite(LED_BUILTIN, HIGH);
  delay(1000);
  digitalWrite(LED_BUILTIN, LOW);
  delay(1000);
}
```

1. Скопируйте код выше в новый скетч
2. Нажмите **Upload** (стрелка вправо) или **Ctrl+U**
3. Дождитесь сообщения "Connecting..."

### Если плата не переходит в режим загрузки автоматически:

1. Нажмите и удерживайте кнопку **BOOT** (на вашей плате)
2. Нажмите кнопку **RST** (Reset)
3. Отпустите кнопку **RST**
4. Отпустите кнопку **BOOT**
5. Быстро нажмите **Upload** в Arduino IDE

## Шаг 8: Проверка работы

1. После успешной загрузки откройте **Serial Monitor**: **Tools** → **Serial Monitor** (или **Ctrl+Shift+M**)
2. Установите скорость: **115200 baud**
3. Нажмите кнопку **RST** на плате
4. Вы должны увидеть вывод в Serial Monitor

## Установка необходимых библиотек

Для вашего проекта нужны библиотеки (обычно уже включены в ESP32 пакет):

1. **WiFi** - встроенная
2. **WebServer** - встроенная

Проверка:
1. **Sketch** → **Include Library** → **Manage Libraries**
2. Найдите "WiFi" и "WebServer" - должны быть установлены

## Возможные проблемы и решения

### Проблема 1: "A fatal error occurred: Failed to connect to ESP32"

**Решение:**
- Используйте качественный USB кабель с поддержкой данных
- Попробуйте другой USB порт на компьютере
- Переведите плату в режим загрузки вручную (BOOT + RST)
- Уменьшите Upload Speed до 115200
- Попробуйте другой USB разъем на плате (USB вместо COM или наоборот)

### Проблема 2: Порт не отображается

**Решение:**
- Установите драйвера CP210x: https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers
- Перезагрузите компьютер
- Попробуйте другой USB кабель

### Проблема 3: "USB CDC On Boot" ошибки

**Решение:**
- Убедитесь что "USB CDC On Boot" = Enabled
- После загрузки скетча плата может сменить COM порт - выберите новый порт

### Проблема 4: Плата постоянно перезагружается

**Решение:**
- Проверьте питание USB (должно быть не менее 500mA)
- Попробуйте питать от внешнего источника 5V на пин VIN

## Следующий шаг

После успешной настройки Arduino IDE и тестовой загрузки:
1. Скопируйте `.env.example` в `.env` и заполните ваши WiFi данные
2. Откройте файл `esp32_cat_follower_simple.ino`
3. Измените WiFi credentials (возьмите значения из .env файла):
   ```cpp
   const char* ssid = "YOUR_WIFI_SSID";      // ваша WiFi сеть (из .env)
   const char* password = "YOUR_WIFI_PASSWORD";    // ваш пароль (из .env)
   ```
4. Загрузите код на ESP32-S3
5. Откройте Serial Monitor (115200 baud)
6. Запишите IP адрес который выдаст ESP32

## Полезные команды для отладки

После загрузки кода в Serial Monitor вы увидите:
```
ESP32 Cat Follower Robot - Starting...
Connecting to WiFi: YOUR_WIFI_SSID
CONNECTED!
IP address: 192.168.1.XXX
Web server started!
Robot is ready!
```

Запишите этот IP адрес - он понадобится для Python скрипта!
