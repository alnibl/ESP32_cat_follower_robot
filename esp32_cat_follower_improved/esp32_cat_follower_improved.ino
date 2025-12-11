// Улучшенная версия кода для ESP32-S3 - Робот следящий за котом
// Версия 2.1 - Исправлен критический баг с обработкой очереди команд
// Изменения в v2.1:
// - ИСПРАВЛЕНО: Очередь команд теперь обрабатывается правильно (убрана проверка !autoStopEnabled)
// - ДОБАВЛЕНО: Детальное логирование всех команд для диагностики
// - ОПТИМИЗИРОВАНО: Уменьшены таймеры автостопа (forward: 1.5с, turn: 0.4с)
// - ДОБАВЛЕНО: Счетчик интерфейсов команд для отслеживания пропусков
//
// Изменения в v2.0:
// - Заменены блокирующие delay() на неблокирующие проверки времени
// - Добавлена очередь команд для предотвращения потерь
// - Улучшено логирование для отладки
// - Исправлена проблема с миганием LED и пропуском backward команд

#include <WiFi.h>
#include <WebServer.h>

// ===== НАСТРОЙТЕ ЭТИ ПАРАМЕТРЫ =====
// ВАЖНО: Используйте значения из файла .env (загрузите его локально, не коммитьте в Git!)
// IMPORTANT: Use values from .env file (load it locally, don't commit to Git!)
const char* ssid = "   ";      // Замените на имя вашей WiFi сети
const char* password = "   ";   // Замените на пароль вашей WiFi

// ===== ПИНЫ ДЛЯ ПОДКЛЮЧЕНИЯ МОТОРОВ =====
// ВАЖНО! На ESP32-S3 GPIO 26-32 используются для Flash/PSRAM - не использовать!
// Безопасные пины: GPIO 1-18, 33-48 (кроме 19,20 если нужен USB)

// Левый мотор
const int leftMotorPin1 = 1;    // Подключите к IN1 на MX1508 (GPIO1)
const int leftMotorPin2 = 2;    // Подключите к IN2 на MX1508 (GPIO2)

// Правый мотор
const int rightMotorPin1 = 42;  // Подключите к IN3 на MX1508 (GPIO42)
const int rightMotorPin2 = 41;  // Подключите к IN4 на MX1508 (GPIO41)

// Веб сервер на стандартном порту 80
WebServer server(80);

// Переменная для скорости (0-255)
int motorSpeed = 150;  // Скорость для forward/backward
int turnSpeed = 230;   // Увеличенная скорость для поворотов (зафиксированное колесо)

// Переменная для отслеживания текущего состояния моторов
enum MotorState { STOPPED, FORWARD, BACKWARD, LEFT, RIGHT };
MotorState currentState = STOPPED;

// Таймер для автоматической остановки
unsigned long motorStartTime = 0;  // Время начала движения
unsigned long motorDuration = 0;   // Длительность движения (мс)
bool autoStopEnabled = false;      // Включена ли автоостановка

// ===== НОВОЕ: Неблокирующая смена направления =====
unsigned long directionChangeStartTime = 0;
bool waitingForDirectionChange = false;
MotorState pendingState = STOPPED;
int pendingSpeed = 0;
const unsigned long DIRECTION_CHANGE_DELAY = 150; // 150мс пауза

// ===== НОВОЕ: Очередь команд =====
const int COMMAND_QUEUE_SIZE = 5;
struct Command {
  MotorState action;
  int speed;
  bool valid;
};
Command commandQueue[COMMAND_QUEUE_SIZE];
int queueHead = 0;  // Индекс для добавления
int queueTail = 0;  // Индекс для извлечения
int queueCount = 0; // Количество команд в очереди

// ===== НОВОЕ v2.1: Расширенная статистика для отладки =====
unsigned long totalCommands = 0;
unsigned long droppedCommands = 0;
unsigned long executedCommands = 0;
unsigned long queuedCommands = 0;  // Счетчик команд добавленных в очередь
unsigned long commandIdCounter = 0;  // Уникальный ID для каждой команды

void setup() {
  // Запуск последовательного порта для отладки
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n========================================");
  Serial.println("ESP32 Cat Follower Robot v2.1 - Starting...");
  Serial.println("BUGFIX: Queue processing fixed!");
  Serial.println("========================================\n");

  // Настройка пинов моторов как выходы
  pinMode(leftMotorPin1, OUTPUT);
  pinMode(leftMotorPin2, OUTPUT);
  pinMode(rightMotorPin1, OUTPUT);
  pinMode(rightMotorPin2, OUTPUT);

  // Останавливаем моторы при старте
  stopMotors();

  // Инициализация очереди команд
  for (int i = 0; i < COMMAND_QUEUE_SIZE; i++) {
    commandQueue[i].valid = false;
  }

  // Подключение к WiFi
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  // Ждем подключения
  Serial.println("Connecting to WiFi...");

  // Дополнительные подсказки
  WiFi.disconnect(true);
  WiFi.mode(WIFI_STA);
  delay(1000);

  WiFi.begin(ssid, password);

  // Бесконечное ожидание подключения c выводом статуса
  int counter = 0;
  while (WiFi.status() != WL_CONNECTED) {
      counter++;
      Serial.print("Attempt ");
      Serial.print(counter);
      Serial.print(" - Status: ");
      Serial.println(WiFi.status());
      delay(1000);
  }

  Serial.println("\nCONNECTED!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  // Успешное подключение
  Serial.println("\n\nSUCCESS! Connected to WiFi");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
  Serial.println("\nWrite down this IP address!");
  Serial.println("You will need it for Python script\n");

  // Настройка веб-сервера
  setupWebServer();

  // Запуск сервера
  server.begin();
  Serial.println("Web server started!");
  Serial.println("\nTest commands in browser:");
  Serial.print("http://");
  Serial.print(WiFi.localIP());
  Serial.println("/");
  Serial.println("\nRobot is ready!");
  Serial.println("========================================\n");
}

void loop() {
  // Обработка входящих запросов (ВСЕГДА выполняется, не блокируется)
  server.handleClient();

  // ===== НОВОЕ: Проверка неблокирующей задержки смены направления =====
  if (waitingForDirectionChange) {
    if (millis() - directionChangeStartTime >= DIRECTION_CHANGE_DELAY) {
      // Задержка завершена, выполняем отложенную команду
      waitingForDirectionChange = false;
      Serial.println("Direction change delay completed, executing pending command");
      executeMotorCommand(pendingState, pendingSpeed);
    }
  }

  // ===== ИСПРАВЛЕНО v2.1: Обработка очереди команд =====
  // BUGFIX: Убрана проверка !autoStopEnabled - теперь очередь обрабатывается
  // когда мотор остановлен (после истечения таймера автостопа)
  if (!waitingForDirectionChange && queueCount > 0 && currentState == STOPPED) {
    // Извлекаем команду из очереди
    Command cmd = dequeueCommand();
    if (cmd.valid) {
      Serial.print("▶️  Executing queued command: ");
      printMotorState(cmd.action);
      Serial.print(" @ speed ");
      Serial.println(cmd.speed);
      scheduleMotorCommand(cmd.action, cmd.speed);
    }
  }

  // Проверка таймера автоостановки
  if (autoStopEnabled && (millis() - motorStartTime >= motorDuration)) {
    stopMotors();
    autoStopEnabled = false;
    Serial.println("Auto-STOP (timer expired)");
  }

  // Периодический вывод статистики (каждые 30 секунд)
  static unsigned long lastStatsTime = 0;
  if (millis() - lastStatsTime >= 30000) {
    lastStatsTime = millis();
    printStatistics();
  }
}

// ===== НОВЫЕ ФУНКЦИИ: УПРАВЛЕНИЕ ОЧЕРЕДЬЮ КОМАНД =====

bool enqueueCommand(MotorState action, int speed) {
  if (queueCount >= COMMAND_QUEUE_SIZE) {
    Serial.print("❌ Command queue FULL! Dropping: ");
    printMotorState(action);
    Serial.print(" @ ");
    Serial.println(speed);
    droppedCommands++;
    return false;
  }

  commandQueue[queueHead].action = action;
  commandQueue[queueHead].speed = speed;
  commandQueue[queueHead].valid = true;

  queueHead = (queueHead + 1) % COMMAND_QUEUE_SIZE;
  queueCount++;
  queuedCommands++;  // v2.1: Счетчик добавленных в очередь команд

  Serial.print("📝 Command queued: ");
  printMotorState(action);
  Serial.print(" @ ");
  Serial.print(speed);
  Serial.print(" (queue: ");
  Serial.print(queueCount);
  Serial.print("/");
  Serial.print(COMMAND_QUEUE_SIZE);
  Serial.println(")");

  return true;
}

Command dequeueCommand() {
  Command cmd;
  cmd.valid = false;

  if (queueCount == 0) {
    return cmd;
  }

  cmd = commandQueue[queueTail];
  commandQueue[queueTail].valid = false;

  queueTail = (queueTail + 1) % COMMAND_QUEUE_SIZE;
  queueCount--;

  return cmd;
}

// ===== НОВАЯ ФУНКЦИЯ: Планирование команды мотора =====

void scheduleMotorCommand(MotorState newState, int speed) {
  commandIdCounter++;  // v2.1: Уникальный ID команды
  totalCommands++;
  motorSpeed = speed;

  // v2.1: Детальное логирование входящей команды
  Serial.print("[CMD #");
  Serial.print(commandIdCounter);
  Serial.print("] Received: ");
  printMotorState(newState);
  Serial.print(" @ ");
  Serial.print(speed);
  Serial.print(" | Current state: ");
  printMotorState(currentState);
  Serial.print(" | autoStop: ");
  Serial.println(autoStopEnabled ? "ON" : "OFF");

  // Проверяем, нужна ли пауза перед сменой направления
  bool needsPause = false;

  if (newState == FORWARD && currentState == BACKWARD) {
    needsPause = true;
  } else if (newState == BACKWARD && currentState == FORWARD) {
    needsPause = true;
  }

  if (needsPause && currentState != STOPPED) {
    // Останавливаем моторы и планируем выполнение после паузы
    Serial.println("⚠️  Direction change detected! Scheduling pause (150ms)...");
    stopMotorsImmediate(); // Останавливаем БЕЗ сброса autoStopEnabled
    waitingForDirectionChange = true;
    directionChangeStartTime = millis();
    pendingState = newState;
    pendingSpeed = speed;
  } else if (autoStopEnabled) {
    // v2.1: Если мотор уже движется - добавляем в очередь
    Serial.println("⏳ Motor busy, adding to queue...");
    enqueueCommand(newState, speed);
  } else {
    // Выполняем команду сразу
    executeMotorCommand(newState, speed);
  }
}

// ===== НОВАЯ ФУНКЦИЯ: Выполнение команды мотора =====

void executeMotorCommand(MotorState newState, int speed) {
  motorSpeed = speed;

  switch (newState) {
    case FORWARD:
      moveForwardDirect();
      break;
    case BACKWARD:
      moveBackwardDirect();
      break;
    case LEFT:
      turnLeftDirect();
      break;
    case RIGHT:
      turnRightDirect();
      break;
    case STOPPED:
      stopMotors();
      break;
  }

  executedCommands++;
}

// ===== УЛУЧШЕННЫЕ ФУНКЦИИ УПРАВЛЕНИЯ МОТОРАМИ =====
// (Без блокирующих delay!)

void moveForwardDirect() {
  Serial.print("▶️  Moving FORWARD @ ");
  Serial.print(motorSpeed);
  Serial.println(" PWM (1.5 sec)");  // ОПТИМИЗИРОВАНО v2.1: было 2 сек

  // Левый мотор вперед
  analogWrite(leftMotorPin1, motorSpeed);
  analogWrite(leftMotorPin2, 0);
  // Правый мотор вперед
  analogWrite(rightMotorPin1, motorSpeed);
  analogWrite(rightMotorPin2, 0);

  currentState = FORWARD;

  // Запускаем таймер на 1.5 секунды (ОПТИМИЗИРОВАНО v2.1)
  motorStartTime = millis();
  motorDuration = 1500;  // 1500мс = 1.5 секунды (было 2000)
  autoStopEnabled = true;
}

void moveBackwardDirect() {
  Serial.print("⏪ Moving BACKWARD @ ");
  Serial.print(motorSpeed);
  Serial.println(" PWM (1.5 sec)");

  // Левый мотор назад
  analogWrite(leftMotorPin1, 0);
  analogWrite(leftMotorPin2, motorSpeed);
  // Правый мотор назад
  analogWrite(rightMotorPin1, 0);
  analogWrite(rightMotorPin2, motorSpeed);

  currentState = BACKWARD;

  // Запускаем таймер на 1.5 секунды
  motorStartTime = millis();
  motorDuration = 1500;
  autoStopEnabled = true;
}

void turnLeftDirect() {
  Serial.print("⬅️  Turning LEFT (tank turn) @ ");
  Serial.print(turnSpeed);
  Serial.println(" PWM (0.3 sec)");

  // Левый мотор НАЗАД (tank turn)
  analogWrite(leftMotorPin1, 0);
  analogWrite(leftMotorPin2, turnSpeed);
  // Правый мотор вперед
  analogWrite(rightMotorPin1, turnSpeed);
  analogWrite(rightMotorPin2, 0);

  currentState = LEFT;

  // Запускаем таймер на 0.3 секунды
  motorStartTime = millis();
  motorDuration = 300;
  autoStopEnabled = true;
}

void turnRightDirect() {
  Serial.print("➡️  Turning RIGHT (tank turn) @ ");
  Serial.print(turnSpeed);
  Serial.println(" PWM (0.3 sec)");

  // Левый мотор вперед
  analogWrite(leftMotorPin1, turnSpeed);
  analogWrite(leftMotorPin2, 0);
  // Правый мотор НАЗАД (tank turn)
  analogWrite(rightMotorPin1, 0);
  analogWrite(rightMotorPin2, turnSpeed);

  currentState = RIGHT;

  // Запускаем таймер на 0.3 секунды
  motorStartTime = millis();
  motorDuration = 300;
  autoStopEnabled = true;
}

void stopMotors() {
  Serial.println("STOP");
  // Останавливаем все моторы
  analogWrite(leftMotorPin1, 0);
  analogWrite(leftMotorPin2, 0);
  analogWrite(rightMotorPin1, 0);
  analogWrite(rightMotorPin2, 0);

  currentState = STOPPED;
  autoStopEnabled = false;  // Выключаем автоостановку
}

void stopMotorsImmediate() {
  // Останавливаем моторы БЕЗ сброса флага autoStopEnabled
  // Используется при смене направления
  Serial.println("STOP (immediate, before direction change)");
  analogWrite(leftMotorPin1, 0);
  analogWrite(leftMotorPin2, 0);
  analogWrite(rightMotorPin1, 0);
  analogWrite(rightMotorPin2, 0);

  currentState = STOPPED;
}

// ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====

void printMotorState(MotorState state) {
  switch (state) {
    case FORWARD: Serial.print("FORWARD"); break;
    case BACKWARD: Serial.print("BACKWARD"); break;
    case LEFT: Serial.print("LEFT"); break;
    case RIGHT: Serial.print("RIGHT"); break;
    case STOPPED: Serial.print("STOPPED"); break;
  }
}

void printStatistics() {
  Serial.println("\n========== STATISTICS v2.1 ==========");
  Serial.print("Total commands received: ");
  Serial.println(totalCommands);
  Serial.print("├─ Executed immediately: ");
  Serial.println(executedCommands - queuedCommands);  // v2.1: Команды выполненные сразу
  Serial.print("├─ Queued for later: ");
  Serial.println(queuedCommands);  // v2.1: Команды отложенные в очередь
  Serial.print("├─ Dropped (queue full): ");
  Serial.println(droppedCommands);
  Serial.print("└─ Currently in queue: ");
  Serial.println(queueCount);

  if (totalCommands > 0) {
    float dropRate = (float)droppedCommands / totalCommands * 100;
    float queueRate = (float)queuedCommands / totalCommands * 100;
    Serial.print("\n📊 Drop rate: ");
    Serial.print(dropRate, 2);
    Serial.print("% | Queue rate: ");
    Serial.print(queueRate, 2);
    Serial.println("%");
  }

  Serial.print("\nCurrent motor state: ");
  printMotorState(currentState);
  Serial.print(" | autoStop: ");
  Serial.println(autoStopEnabled ? "ON" : "OFF");

  Serial.println("=====================================\n");
}

// ===== НАСТРОЙКА ВЕБ-СЕРВЕРА =====

void setupWebServer() {
  // Главная страница с AJAX интерфейсом
  server.on("/", []() {
    String html = "<!DOCTYPE html><html><head>";
    html += "<meta charset='UTF-8'>";
    html += "<meta name='viewport' content='width=device-width, initial-scale=1.0'>";
    html += "<title>Cat Robot Control v2.1</title>";
    html += "<style>";
    html += "body { font-family: Arial, sans-serif; max-width: 600px; margin: 20px auto; padding: 20px; background: #f5f5f5; }";
    html += "h1 { color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }";
    html += ".controls { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 20px 0; }";
    html += ".btn { padding: 20px; font-size: 16px; border: none; border-radius: 8px; cursor: pointer; color: white; font-weight: bold; transition: all 0.3s; }";
    html += ".btn:active { transform: scale(0.95); }";
    html += ".btn:disabled { opacity: 0.5; cursor: not-allowed; }";
    html += ".btn-forward { background: #4CAF50; grid-column: 2; }";
    html += ".btn-backward { background: #f44336; grid-column: 2; }";
    html += ".btn-left { background: #FF9800; grid-column: 1; grid-row: 2; }";
    html += ".btn-right { background: #2196F3; grid-column: 3; grid-row: 2; }";
    html += ".btn-stop { background: #9E9E9E; grid-column: 1 / 4; }";
    html += ".stats { background: white; padding: 15px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }";
    html += ".stats h3 { margin-top: 0; color: #333; }";
    html += ".stat-item { margin: 8px 0; padding: 8px; background: #f9f9f9; border-radius: 4px; }";
    html += ".status { padding: 10px; border-radius: 8px; margin: 10px 0; font-weight: bold; text-align: center; }";
    html += ".status.success { background: #c8e6c9; color: #2e7d32; }";
    html += ".status.error { background: #ffcdd2; color: #c62828; }";
    html += ".status.info { background: #bbdefb; color: #1565c0; }";
    html += "#lastCommand { font-size: 14px; color: #666; margin: 10px 0; }";
    html += "</style></head><body>";

    html += "<h1>🤖 ESP32 Cat Robot v2.1</h1>";
    html += "<div class='status info'>⚙️ Fixed wheel mode - Turn: 230 PWM, Move: 150 PWM</div>";
    html += "<p><strong>IP:</strong> " + WiFi.localIP().toString() + "</p>";

    html += "<div id='lastCommand'>Ready to control...</div>";

    html += "<div class='controls'>";
    html += "<button class='btn btn-forward' onclick='sendCommand(\"forward\")'>⬆️<br>Forward<br>(150 PWM)</button>";
    html += "<button class='btn btn-left' onclick='sendCommand(\"left\")'>⬅️<br>Left<br>(230 PWM)</button>";
    html += "<button class='btn btn-right' onclick='sendCommand(\"right\")'>➡️<br>Right<br>(230 PWM)</button>";
    html += "<button class='btn btn-backward' onclick='sendCommand(\"backward\")'>⬇️<br>Backward<br>(150 PWM)</button>";
    html += "<button class='btn btn-stop' onclick='sendCommand(\"stop\")'>⏹️ STOP</button>";
    html += "</div>";

    html += "<div class='stats'>";
    html += "<h3>📊 Statistics (Auto-refresh)</h3>";
    html += "<div class='stat-item'>Total commands: <strong id='statTotal'>-</strong></div>";
    html += "<div class='stat-item'>├─ Executed: <strong id='statExecuted'>-</strong></div>";
    html += "<div class='stat-item'>├─ Queued: <strong id='statQueued'>-</strong></div>";
    html += "<div class='stat-item'>├─ Dropped: <strong id='statDropped'>-</strong></div>";
    html += "<div class='stat-item'>└─ In queue now: <strong id='statQueueNow'>-</strong>/5</div>";
    html += "<div class='stat-item'>Motor state: <strong id='statState'>-</strong></div>";
    html += "</div>";

    html += "<script>";
    html += "function sendCommand(action) {";
    html += "  var speed = " + String(motorSpeed) + ";";
    html += "  if (action === 'left' || action === 'right') { speed = " + String(turnSpeed) + "; }";
    html += "  fetch('/command?action=' + action + '&speed=' + speed)";
    html += "    .then(r => r.json())";
    html += "    .then(data => {";
    html += "      document.getElementById('lastCommand').textContent = '✅ Sent: ' + action.toUpperCase() + ' @ ' + speed + ' PWM';";
    html += "      document.getElementById('lastCommand').style.color = '#2e7d32';";
    html += "      updateStats();";
    html += "    })";
    html += "    .catch(err => {";
    html += "      document.getElementById('lastCommand').textContent = '❌ Error: ' + err.message;";
    html += "      document.getElementById('lastCommand').style.color = '#c62828';";
    html += "    });";
    html += "}";
    html += "function updateStats() {";
    html += "  fetch('/stats')";
    html += "    .then(r => r.json())";
    html += "    .then(data => {";
    html += "      document.getElementById('statTotal').textContent = data.total_commands;";
    html += "      document.getElementById('statExecuted').textContent = data.executed;";
    html += "      const queued = data.total_commands - data.executed - data.dropped;";
    html += "      document.getElementById('statQueued').textContent = queued;";
    html += "      document.getElementById('statDropped').textContent = data.dropped + (data.dropped === 0 ? ' ✅' : ' ❌');";
    html += "      document.getElementById('statQueueNow').textContent = data.queue_size;";
    html += "      document.getElementById('statState').textContent = data.current_state;";
    html += "    });";
    html += "}";
    html += "updateStats();";
    html += "setInterval(updateStats, 2000);";
    html += "</script>";
    html += "</body></html>";

    server.send(200, "text/html", html);
  });

  // Команда вперед
  server.on("/forward", []() {
    scheduleMotorCommand(FORWARD, motorSpeed);
    server.send(200, "text/plain", "Moving forward");
  });

  // Команда назад
  server.on("/backward", []() {
    scheduleMotorCommand(BACKWARD, motorSpeed);
    server.send(200, "text/plain", "Moving backward");
  });

  // Команда влево
  server.on("/left", []() {
    scheduleMotorCommand(LEFT, motorSpeed);
    server.send(200, "text/plain", "Turning left");
  });

  // Команда вправо
  server.on("/right", []() {
    scheduleMotorCommand(RIGHT, motorSpeed);
    server.send(200, "text/plain", "Turning right");
  });

  // Команда стоп
  server.on("/stop", []() {
    scheduleMotorCommand(STOPPED, motorSpeed);
    server.send(200, "text/plain", "Stopped");
  });

  // Установка скорости
  server.on("/speed", []() {
    if (server.hasArg("value")) {
      motorSpeed = server.arg("value").toInt();
      if (motorSpeed < 0) motorSpeed = 0;
      if (motorSpeed > 255) motorSpeed = 255;
      Serial.print("Speed set to: ");
      Serial.println(motorSpeed);
      server.send(200, "text/plain", "Speed: " + String(motorSpeed));
    } else {
      server.send(400, "text/plain", "Need speed value");
    }
  });

  // Универсальная команда для Python
  server.on("/command", []() {
    String response = "{";

    if (server.hasArg("action")) {
      String action = server.arg("action");

      // Если передана скорость, устанавливаем её
      int cmdSpeed = motorSpeed;
      if (server.hasArg("speed")) {
        cmdSpeed = server.arg("speed").toInt();
        if (cmdSpeed < 0) cmdSpeed = 0;
        if (cmdSpeed > 255) cmdSpeed = 255;
      }

      // Выполняем действие
      if (action == "forward") {
        scheduleMotorCommand(FORWARD, cmdSpeed);
        response += "\"status\":\"ok\",\"action\":\"forward\"";
      } else if (action == "backward") {
        scheduleMotorCommand(BACKWARD, cmdSpeed);
        response += "\"status\":\"ok\",\"action\":\"backward\"";
      } else if (action == "left") {
        scheduleMotorCommand(LEFT, cmdSpeed);
        response += "\"status\":\"ok\",\"action\":\"left\"";
      } else if (action == "right") {
        scheduleMotorCommand(RIGHT, cmdSpeed);
        response += "\"status\":\"ok\",\"action\":\"right\"";
      } else if (action == "stop") {
        scheduleMotorCommand(STOPPED, cmdSpeed);
        response += "\"status\":\"ok\",\"action\":\"stop\"";
      } else {
        response += "\"status\":\"error\",\"message\":\"Unknown action\"";
      }
    } else {
      response += "\"status\":\"error\",\"message\":\"No action\"";
    }

    response += ",\"speed\":" + String(motorSpeed);
    response += ",\"queue\":" + String(queueCount);
    response += ",\"dropped\":" + String(droppedCommands);
    response += "}";

    server.send(200, "application/json", response);
  });

  // НОВОЕ: Endpoint для получения статистики
  server.on("/stats", []() {
    String json = "{";
    json += "\"total_commands\":" + String(totalCommands);
    json += ",\"executed\":" + String(executedCommands);
    json += ",\"dropped\":" + String(droppedCommands);
    json += ",\"queue_size\":" + String(queueCount);
    json += ",\"current_state\":\"";
    switch (currentState) {
      case FORWARD: json += "FORWARD"; break;
      case BACKWARD: json += "BACKWARD"; break;
      case LEFT: json += "LEFT"; break;
      case RIGHT: json += "RIGHT"; break;
      case STOPPED: json += "STOPPED"; break;
    }
    json += "\"";
    json += ",\"waiting_for_change\":" + String(waitingForDirectionChange ? "true" : "false");
    json += ",\"auto_stop_enabled\":" + String(autoStopEnabled ? "true" : "false");
    json += "}";

    server.send(200, "application/json", json);
  });
}
