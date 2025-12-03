// Простая версия кода для ESP32-S3 - Робот следящий за котом
// Версия для начинающих с подробными комментариями

#include <WiFi.h>
#include <WebServer.h>

// ===== НАСТРОЙТЕ ЭТИ ПАРАМЕТРЫ =====
// ВАЖНО: Используйте значения из файла .env (загрузите его локально, не коммитьте в Git!)
// IMPORTANT: Use values from .env file (load it locally, don't commit to Git!)
const char* ssid = "YOUR_WIFI_SSID";      // Замените на имя вашей WiFi сети
const char* password = "YOUR_WIFI_PASSWORD";   // Замените на пароль вашей WiFi

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
int motorSpeed = 150;

// Переменная для отслеживания текущего состояния моторов
enum MotorState { STOPPED, FORWARD, BACKWARD, LEFT, RIGHT };
MotorState currentState = STOPPED;

// Таймер для автоматической остановки
unsigned long motorStartTime = 0;  // Время начала движения
unsigned long motorDuration = 0;   // Длительность движения (мс)
bool autoStopEnabled = false;      // Включена ли автоостановка

void setup() {
  // Запуск последовательного порта для отладки
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n========================================");
  Serial.println("ESP32 Cat Follower Robot - Starting...");
  Serial.println("========================================\n");
  
  // Настройка пинов моторов как выходы
  pinMode(leftMotorPin1, OUTPUT);
  pinMode(leftMotorPin2, OUTPUT);
  pinMode(rightMotorPin1, OUTPUT);
  pinMode(rightMotorPin2, OUTPUT);
  
  // Останавливаем моторы при старте
  stopMotors();
  
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
  // Обработка входящих запросов
  server.handleClient();

  // Проверка таймера автоостановки
  if (autoStopEnabled && (millis() - motorStartTime >= motorDuration)) {
    stopMotors();
    autoStopEnabled = false;
    Serial.println("Auto-STOP (timer expired)");
  }
}

// ===== ФУНКЦИИ УПРАВЛЕНИЯ МОТОРАМИ =====

void moveForward() {
  // Если едем назад - сначала остановка!
  if (currentState == BACKWARD) {
    Serial.println("Auto-STOP before direction change");
    stopMotors();
    delay(150);  // Пауза 150мс для полной остановки
  }

  Serial.println("Moving FORWARD (2 sec)");
  // Левый мотор вперед
  analogWrite(leftMotorPin1, motorSpeed);
  analogWrite(leftMotorPin2, 0);
  // Правый мотор вперед
  analogWrite(rightMotorPin1, motorSpeed);
  analogWrite(rightMotorPin2, 0);

  currentState = FORWARD;

  // Запускаем таймер на 2 секунды
  motorStartTime = millis();
  motorDuration = 2000;  // 2000мс = 2 секунды
  autoStopEnabled = true;
}

void moveBackward() {
  // Если едем вперед - сначала остановка!
  if (currentState == FORWARD) {
    Serial.println("Auto-STOP before direction change");
    stopMotors();
    delay(150);  // Пауза 150мс для полной остановки
  }

  Serial.println("Moving BACKWARD (2 sec)");
  // Левый мотор назад
  analogWrite(leftMotorPin1, 0);
  analogWrite(leftMotorPin2, motorSpeed);
  // Правый мотор назад
  analogWrite(rightMotorPin1, 0);
  analogWrite(rightMotorPin2, motorSpeed);

  currentState = BACKWARD;

  // Запускаем таймер на 2 секунды
  motorStartTime = millis();
  motorDuration = 2000;  // 2000мс = 2 секунды
  autoStopEnabled = true;
}

void turnLeft() {
  Serial.println("Turning LEFT (0.5 sec)");
  // Левый мотор медленнее или стоп
  analogWrite(leftMotorPin1, 0);
  analogWrite(leftMotorPin2, 0);
  // Правый мотор вперед
  analogWrite(rightMotorPin1, motorSpeed);
  analogWrite(rightMotorPin2, 0);

  currentState = LEFT;

  // Запускаем таймер на 0.5 секунды
  motorStartTime = millis();
  motorDuration = 500;  // 500мс = 0.5 секунды
  autoStopEnabled = true;
}

void turnRight() {
  Serial.println("Turning RIGHT (0.5 sec)");
  // Левый мотор вперед
  analogWrite(leftMotorPin1, motorSpeed);
  analogWrite(leftMotorPin2, 0);
  // Правый мотор медленнее или стоп
  analogWrite(rightMotorPin1, 0);
  analogWrite(rightMotorPin2, 0);

  currentState = RIGHT;

  // Запускаем таймер на 0.5 секунды
  motorStartTime = millis();
  motorDuration = 500;  // 500мс = 0.5 секунды
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

// ===== НАСТРОЙКА ВЕБ-СЕРВЕРА =====

void setupWebServer() {
  // Главная страница
  server.on("/", []() {
    String html = "<html><head><title>Cat Robot Control</title></head><body>";
    html += "<h1>ESP32 Cat Following Robot</h1>";
    html += "<p>IP Address: " + WiFi.localIP().toString() + "</p>";
    html += "<h2>Test Commands:</h2>";
    html += "<ul>";
    html += "<li><a href='/forward'>Move Forward</a></li>";
    html += "<li><a href='/backward'>Move Backward</a></li>";
    html += "<li><a href='/left'>Turn Left</a></li>";
    html += "<li><a href='/right'>Turn Right</a></li>";
    html += "<li><a href='/stop'>Stop</a></li>";
    html += "</ul>";
    html += "<p>Current Speed: " + String(motorSpeed) + "</p>";
    html += "</body></html>";
    server.send(200, "text/html", html);
  });
  
  // Команда вперед
  server.on("/forward", []() {
    moveForward();
    server.send(200, "text/plain", "Moving forward");
  });
  
  // Команда назад
  server.on("/backward", []() {
    moveBackward();
    server.send(200, "text/plain", "Moving backward");
  });
  
  // Команда влево
  server.on("/left", []() {
    turnLeft();
    server.send(200, "text/plain", "Turning left");
  });
  
  // Команда вправо
  server.on("/right", []() {
    turnRight();
    server.send(200, "text/plain", "Turning right");
  });
  
  // Команда стоп
  server.on("/stop", []() {
    stopMotors();
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
      if (server.hasArg("speed")) {
        motorSpeed = server.arg("speed").toInt();
        if (motorSpeed < 0) motorSpeed = 0;
        if (motorSpeed > 255) motorSpeed = 255;
      }
      
      // Выполняем действие
      if (action == "forward") {
        moveForward();
        response += "\"status\":\"ok\",\"action\":\"forward\"";
      } else if (action == "backward") {
        moveBackward();
        response += "\"status\":\"ok\",\"action\":\"backward\"";
      } else if (action == "left") {
        turnLeft();
        response += "\"status\":\"ok\",\"action\":\"left\"";
      } else if (action == "right") {
        turnRight();
        response += "\"status\":\"ok\",\"action\":\"right\"";
      } else if (action == "stop") {
        stopMotors();
        response += "\"status\":\"ok\",\"action\":\"stop\"";
      } else {
        response += "\"status\":\"error\",\"message\":\"Unknown action\"";
      }
    } else {
      response += "\"status\":\"error\",\"message\":\"No action\"";
    }
    
    response += ",\"speed\":" + String(motorSpeed);
    response += "}";
    
    server.send(200, "application/json", response);
  });
}
