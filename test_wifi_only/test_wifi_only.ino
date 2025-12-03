// Тестовый скрипт для проверки WiFi подключения ESP32-S3
// Загрузите этот код ПЕРВЫМ перед подключением моторов

#include <WiFi.h>
#include <WebServer.h>

// ===== НАСТРОЙТЕ ЭТИ ПАРАМЕТРЫ =====
// ВАЖНО: Используйте значения из файла .env (загрузите его локально, не коммитьте в Git!)
// IMPORTANT: Use values from .env file (load it locally, don't commit to Git!)
const char* ssid = "YOUR_WIFI_SSID";      // Замените на имя вашей WiFi сети
const char* password = "YOUR_WIFI_PASSWORD";      // Замените на пароль вашей WiFi

// Встроенный светодиод (если есть на вашей плате)
const int ledPin = 48;  // RGB LED на ESP32-S3

// Веб сервер
WebServer server(80);

void setup() {
  // Запуск Serial для отладки
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n\n========================================");
  Serial.println("ESP32-S3 WiFi Test");
  Serial.println("========================================\n");

  // Настройка LED
  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, LOW);

  // Подключение к WiFi
  Serial.print("Connecting to: ");
  Serial.println(ssid);

  // Сброс настроек WiFi и установка режима
  WiFi.disconnect(true);
  WiFi.mode(WIFI_STA);
  delay(1000);

  WiFi.begin(ssid, password);

  // Ожидание подключения
  int counter = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");

    // Мигаем LED во время подключения
    digitalWrite(ledPin, !digitalRead(ledPin));

    counter++;
    if (counter % 10 == 0) {
      Serial.println();
      Serial.print("Attempt ");
      Serial.print(counter / 2);
      Serial.print(" - Status code: ");
      Serial.println(WiFi.status());
    }

    // Если долго не подключается, пробуем снова
    if (counter > 60) {
      Serial.println("\nReconnecting...");
      WiFi.disconnect();
      delay(1000);
      WiFi.begin(ssid, password);
      counter = 0;
    }
  }

  // Подключено!
  digitalWrite(ledPin, HIGH);  // LED горит постоянно

  Serial.println("\n\n========================================");
  Serial.println("SUCCESSFULLY CONNECTED TO WiFi!");
  Serial.println("========================================");
  Serial.print("SSID: ");
  Serial.println(WiFi.SSID());
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
  Serial.print("Signal Strength (RSSI): ");
  Serial.print(WiFi.RSSI());
  Serial.println(" dBm");
  Serial.print("MAC Address: ");
  Serial.println(WiFi.macAddress());
  Serial.println("========================================\n");

  // Настройка веб-сервера
  setupWebServer();

  // Запуск сервера
  server.begin();
  Serial.println("Web server started!\n");
  Serial.println("Open in your browser:");
  Serial.print("http://");
  Serial.println(WiFi.localIP());
  Serial.println("\n========================================");
  Serial.println("Test is complete! ESP32-S3 is ready!");
  Serial.println("========================================\n");
}

void loop() {
  // Обработка веб-запросов
  server.handleClient();

  // Проверка подключения
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected! Reconnecting...");
    digitalWrite(ledPin, LOW);
    WiFi.reconnect();
    delay(5000);
  }
}

void setupWebServer() {
  // Главная страница
  server.on("/", []() {
    String html = "<!DOCTYPE html><html><head>";
    html += "<title>ESP32-S3 Test</title>";
    html += "<meta charset='utf-8'>";
    html += "<style>";
    html += "body { font-family: Arial; margin: 40px; background: #f0f0f0; }";
    html += "h1 { color: #333; }";
    html += ".info { background: white; padding: 20px; border-radius: 10px; margin: 10px 0; }";
    html += ".success { color: green; font-weight: bold; }";
    html += "a { display: inline-block; margin: 5px; padding: 10px 20px; ";
    html += "background: #4CAF50; color: white; text-decoration: none; border-radius: 5px; }";
    html += "a:hover { background: #45a049; }";
    html += "</style></head><body>";

    html += "<h1>🎉 ESP32-S3 WiFi Test</h1>";
    html += "<div class='info'>";
    html += "<p class='success'>✓ WiFi Connected Successfully!</p>";
    html += "<p><strong>IP Address:</strong> " + WiFi.localIP().toString() + "</p>";
    html += "<p><strong>SSID:</strong> " + String(ssid) + "</p>";
    html += "<p><strong>Signal:</strong> " + String(WiFi.RSSI()) + " dBm</p>";
    html += "<p><strong>MAC:</strong> " + WiFi.macAddress() + "</p>";
    html += "</div>";

    html += "<h2>Test LED Control</h2>";
    html += "<div class='info'>";
    html += "<a href='/led/on'>LED ON</a>";
    html += "<a href='/led/off'>LED OFF</a>";
    html += "<a href='/led/blink'>LED Blink</a>";
    html += "</div>";

    html += "<h2>Test API Response</h2>";
    html += "<div class='info'>";
    html += "<p>Try: <code>http://" + WiFi.localIP().toString() + "/status</code></p>";
    html += "</div>";

    html += "</body></html>";

    server.send(200, "text/html", html);
    Serial.println("Page requested: /");
  });

  // Управление LED
  server.on("/led/on", []() {
    digitalWrite(ledPin, HIGH);
    Serial.println("LED: ON - Pin state should be HIGH");
    Serial.print("Actual pin read: ");
    Serial.println(digitalRead(ledPin));
    server.send(200, "text/plain", "LED is ON");
  });

  server.on("/led/off", []() {
    digitalWrite(ledPin, LOW);
    Serial.println("LED: OFF - Pin state should be LOW");
    Serial.print("Actual pin read: ");
    Serial.println(digitalRead(ledPin));
    server.send(200, "text/plain", "LED is OFF");
  });

  server.on("/led/blink", []() {
    Serial.println("LED: Blinking");
    for (int i = 0; i < 10; i++) {
      digitalWrite(ledPin, HIGH);
      delay(100);
      digitalWrite(ledPin, LOW);
      delay(100);
    }
    digitalWrite(ledPin, LOW);  // Убедимся что выключили в конце
    Serial.println("LED: Blink complete, should be OFF now");
    server.send(200, "text/plain", "LED blinked 10 times");
  });

  // Статус в JSON формате
  server.on("/status", []() {
    String json = "{";
    json += "\"status\":\"ok\",";
    json += "\"wifi_connected\":true,";
    json += "\"ip\":\"" + WiFi.localIP().toString() + "\",";
    json += "\"ssid\":\"" + String(ssid) + "\",";
    json += "\"rssi\":" + String(WiFi.RSSI()) + ",";
    json += "\"mac\":\"" + WiFi.macAddress() + "\"";
    json += "}";

    server.send(200, "application/json", json);
    Serial.println("Status requested");
  });

  // 404 handler
  server.onNotFound([]() {
    server.send(404, "text/plain", "404: Not Found");
    Serial.println("404 - Page not found");
  });
}
