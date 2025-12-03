#include <WiFi.h>
#include <WebServer.h>

// WiFi настройки
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Пины для моторов
const int motor1Pin1 = 12; // IN1
const int motor1Pin2 = 14; // IN2
const int motor2Pin1 = 27; // IN3
const int motor2Pin2 = 26; // IN4

// PWM настройки
const int freq = 30000;
const int pwmChannel1 = 0;
const int pwmChannel2 = 1;
const int pwmChannel3 = 2;
const int pwmChannel4 = 3;
const int resolution = 8;

// Веб сервер на порту 80
WebServer server(80);

// Скорость моторов (0-255)
int motorSpeed = 200;

void setup() {
  Serial.begin(115200);
  
  // Настройка пинов моторов
  pinMode(motor1Pin1, OUTPUT);
  pinMode(motor1Pin2, OUTPUT);
  pinMode(motor2Pin1, OUTPUT);
  pinMode(motor2Pin2, OUTPUT);
  
  // Настройка PWM
  ledcSetup(pwmChannel1, freq, resolution);
  ledcSetup(pwmChannel2, freq, resolution);
  ledcSetup(pwmChannel3, freq, resolution);
  ledcSetup(pwmChannel4, freq, resolution);
  
  ledcAttachPin(motor1Pin1, pwmChannel1);
  ledcAttachPin(motor1Pin2, pwmChannel2);
  ledcAttachPin(motor2Pin1, pwmChannel3);
  ledcAttachPin(motor2Pin2, pwmChannel4);
  
  // Подключение к WiFi
  WiFi.begin(ssid, password);
  Serial.println("Connecting to WiFi...");
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }
  
  Serial.println("\nConnected to WiFi");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
  
  // Настройка маршрутов веб-сервера
  server.on("/", handleRoot);
  server.on("/forward", handleForward);
  server.on("/backward", handleBackward);
  server.on("/left", handleLeft);
  server.on("/right", handleRight);
  server.on("/stop", handleStop);
  server.on("/speed", handleSpeed);
  server.on("/command", handleCommand);
  
  server.begin();
  Serial.println("HTTP server started");
  
  // Стоп моторов при старте
  stopMotors();
}

void loop() {
  server.handleClient();
}

// Функции управления моторами
void forward() {
  ledcWrite(pwmChannel1, motorSpeed);
  ledcWrite(pwmChannel2, 0);
  ledcWrite(pwmChannel3, motorSpeed);
  ledcWrite(pwmChannel4, 0);
}

void backward() {
  ledcWrite(pwmChannel1, 0);
  ledcWrite(pwmChannel2, motorSpeed);
  ledcWrite(pwmChannel3, 0);
  ledcWrite(pwmChannel4, motorSpeed);
}

void turnLeft() {
  ledcWrite(pwmChannel1, 0);
  ledcWrite(pwmChannel2, motorSpeed/2);
  ledcWrite(pwmChannel3, motorSpeed);
  ledcWrite(pwmChannel4, 0);
}

void turnRight() {
  ledcWrite(pwmChannel1, motorSpeed);
  ledcWrite(pwmChannel2, 0);
  ledcWrite(pwmChannel3, 0);
  ledcWrite(pwmChannel4, motorSpeed/2);
}

void stopMotors() {
  ledcWrite(pwmChannel1, 0);
  ledcWrite(pwmChannel2, 0);
  ledcWrite(pwmChannel3, 0);
  ledcWrite(pwmChannel4, 0);
}

// HTTP обработчики
void handleRoot() {
  String html = "<html><body>";
  html += "<h1>ESP32 Robot Control</h1>";
  html += "<p>IP: " + WiFi.localIP().toString() + "</p>";
  html += "<p>Commands: /forward, /backward, /left, /right, /stop</p>";
  html += "<p>Speed: /speed?value=0-255</p>";
  html += "<p>Direct: /command?action=forward&speed=200</p>";
  html += "</body></html>";
  server.send(200, "text/html", html);
}

void handleForward() {
  forward();
  server.send(200, "text/plain", "Moving forward");
}

void handleBackward() {
  backward();
  server.send(200, "text/plain", "Moving backward");
}

void handleLeft() {
  turnLeft();
  server.send(200, "text/plain", "Turning left");
}

void handleRight() {
  turnRight();
  server.send(200, "text/plain", "Turning right");
}

void handleStop() {
  stopMotors();
  server.send(200, "text/plain", "Stopped");
}

void handleSpeed() {
  if (server.hasArg("value")) {
    motorSpeed = server.arg("value").toInt();
    motorSpeed = constrain(motorSpeed, 0, 255);
    server.send(200, "text/plain", "Speed set to: " + String(motorSpeed));
  } else {
    server.send(400, "text/plain", "Missing speed value");
  }
}

// Универсальный обработчик команд для Python
void handleCommand() {
  String response = "{";
  
  if (server.hasArg("action")) {
    String action = server.arg("action");
    
    if (server.hasArg("speed")) {
      motorSpeed = server.arg("speed").toInt();
      motorSpeed = constrain(motorSpeed, 0, 255);
    }
    
    if (action == "forward") {
      forward();
      response += "\"status\":\"ok\",\"action\":\"forward\"";
    } else if (action == "backward") {
      backward();
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
    response += "\"status\":\"error\",\"message\":\"No action specified\"";
  }
  
  response += ",\"speed\":" + String(motorSpeed);
  response += "}";
  
  server.send(200, "application/json", response);
}
