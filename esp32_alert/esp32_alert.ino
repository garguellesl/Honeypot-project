/*
  esp32_alert.ino
  ----------------------------------------------------------------------
  Complemento físico para el Honeypot IoT.

  El ESP32 consulta periódicamente la API del dashboard Flask
  (/api/stats) y, si el número total de intentos ha aumentado desde la
  última consulta, enciende un LED y activa un buzzer durante 1.5s.

  Así el proyecto deja de ser "solo software": conecta la parte de
  ciberseguridad con la parte de electrónica/robótica.

  Conexionado:
    LED      -> GPIO 2  (+ resistencia 220ohm a GND)
    Buzzer   -> GPIO 4
    GND      -> GND común

  Configura SSID, PASSWORD y DASHBOARD_HOST antes de subir el sketch.
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

const char* SSID            = "TU_WIFI";
const char* PASSWORD        = "TU_PASSWORD";
const char* DASHBOARD_HOST  = "192.168.1.50";   // IP del Raspberry Pi
const uint16_t DASHBOARD_PORT = 5000;
const uint32_t POLL_INTERVAL_MS = 5000;

const int PIN_LED    = 2;
const int PIN_BUZZER = 4;

long lastTotal = -1;

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(SSID, PASSWORD);
  Serial.print("Conectando a WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(400);
    Serial.print(".");
  }
  Serial.println("\nConectado: " + WiFi.localIP().toString());
}

void triggerAlert() {
  digitalWrite(PIN_LED, HIGH);
  digitalWrite(PIN_BUZZER, HIGH);
  delay(1500);
  digitalWrite(PIN_LED, LOW);
  digitalWrite(PIN_BUZZER, LOW);
}

void checkHoneypot() {
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  String url = String("http://") + DASHBOARD_HOST + ":" + DASHBOARD_PORT + "/api/stats";
  http.begin(url);
  int code = http.GET();

  if (code == 200) {
    String payload = http.getString();
    StaticJsonDocument<512> doc;
    DeserializationError err = deserializeJson(doc, payload);
    if (!err) {
      long total = doc["total"] | -1;
      if (lastTotal >= 0 && total > lastTotal) {
        Serial.printf("Nuevo ataque detectado! total=%ld\n", total);
        triggerAlert();
      }
      lastTotal = total;
    }
  } else {
    Serial.printf("Error consultando dashboard: %d\n", code);
  }
  http.end();
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  connectWiFi();
}

void loop() {
  checkHoneypot();
  delay(POLL_INTERVAL_MS);
}
