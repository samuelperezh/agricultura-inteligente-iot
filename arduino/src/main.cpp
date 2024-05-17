// Librerías
#include <Arduino.h>
#include <Wire.h>
#include <ClosedCube_HDC1080.h>
#include <TinyGPS++.h>
#include <WiFi.h>
#include <utility>
#include <ArduinoJson.h>
#include <Ai_AP3216_AmbientLightAndProximity.h>

// Declaraciones
static void smartDelay(unsigned long ms);
void send_data(const char* id, const char* atributo1, const char* atributo2, float valor1, float valor2 = 0);
void leerGPS(void);
float leerHumedadAmbiental(int n);
float leerTemperatura(int n);
float leerLuz(int n);
float leerProximidad(int n);
float leerHumedadPlanta(int n);
const int analogPin = 33;
const int ledPin = 25;
static const uint32_t GPSBaud = 9600;
const char* server = "54.227.149.158";
const char* ssid = "UPBWiFi";
int estado = 0;
const int prunning = 10;
float temperatura, humedad, luz, proximidad, humedad_planta, latitud, longitud;
int moisturePin = 33;
float moistureLevel;
unsigned long lastSendTime = 0;

// Variables
TinyGPSPlus gps;
ClosedCube_HDC1080 sensorHT;
WiFiClient client;
JsonDocument doc;
Ai_AP3216_AmbientLightAndProximity aps = Ai_AP3216_AmbientLightAndProximity();

// Función inicio
void setup() {
  Serial.begin(115200);
  Serial1.begin(GPSBaud, SERIAL_8N1, 34, 12);
  Wire.begin(4, 0);
  sensorHT.begin(0x40);
  aps.begin();
	aps.startAmbientLightAndProximitySensor ();
  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, LOW);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, "");
  Serial.println("Conectando a la red WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    Serial.println("Intentando conectar a la red WiFi...");
    delay(100);
  }
  Serial.println("Conectado a la red WiFi");
  estado = 1;
}

void loop() {
  unsigned long currentTime = millis();
  if (currentTime - lastSendTime >= 30000 || lastSendTime == 0) {
    lastSendTime = currentTime;
    estado = 1;
    while (estado <= 4) {
      switch(estado) {
        case 1:
          Serial.println("1. Leyendo datos de los sensores de Humedad, Temperatura, Luz y Proximidad");
          temperatura = leerTemperatura(10);
          humedad = leerHumedadAmbiental(10);
          luz = leerLuz(10);
          proximidad = leerProximidad(10);
          humedad_planta = leerHumedadPlanta(10);
          estado = 2;
          break;
        case 2:
          Serial.println("2. Leyendo datos del GPS");
          leerGPS();
          estado = 3;
          break;
        case 3:
          Serial.println("3. Enviando datos al servidor");
          send_data("sensorTemperatura", "temperatura", NULL, temperatura);
          send_data("sensorHumedad", "humedad", NULL, humedad);
          send_data("sensorLuz", "luz", NULL, luz);
          send_data("sensorProximidad", "proximidad", NULL, proximidad);
          send_data("sensorHumedadPlanta", "humedad", NULL, humedad_planta);
          send_data("sensorGPS", "latitud", "longitud", latitud, longitud);
          estado = 4;
          break;
        case 4:
          Serial.println("4. Durmiendo");
          estado = 5;
          break;
        default:
          Serial.println("No capturo estados");
          break;
      }
    }
  }
}

// Función de retardo
static void smartDelay(unsigned long ms) {
  unsigned long start = millis();
  do {
    while (Serial1.available())
      gps.encode(Serial1.read());
  } while (millis() - start < ms);
}

// Función para enviar datos al servidor
void send_data(const char* id, const char* atributo1, const char* atributo2, float valor1, float valor2) {
  doc.clear();
  JsonObject sendObj = doc[atributo1].to<JsonObject>();
  sendObj["type"] = "numeric";
  sendObj["value"] = valor1;
  if (atributo2 != NULL) {
    JsonObject sendObj2 = doc[atributo2].to<JsonObject>();
    sendObj2["type"] = "numeric";
    sendObj2["value"] = valor2;
  }
  String postData;
  serializeJson(doc, postData);

  while (true) {
    if (client.connect(server, 1026)) {
      client.println("PATCH /v2/entities/" + String(id) + "/attrs HTTP/1.1");
      client.println("Host: " + String(server));
      client.println("Content-Type: application/json");
      client.println("Content-Length: " + String(postData.length()));
      client.println();
      client.println(postData);
      Serial.println(postData);

      delay(500);
      if (client.available()) {
        String line = client.readStringUntil('\n');
        Serial.println(line);
        if (line.startsWith("HTTP")) {
          break;
        }
      }
    }
    else {
      Serial.println("Fallo al conectar al servidor, reintentando...");
    }
    delay(2000);
  }

  while (client.available()) {
    String line = client.readStringUntil('\n');
    Serial.println(line);
  }
  delay(2000);
}

// Función para leer datos del GPS
void leerGPS() {
  smartDelay(100);
  latitud = gps.location.lat();
  Serial.println("Latitud: " + String(latitud));
  longitud = gps.location.lng();
  Serial.println("Longitud: " + String(longitud));
  Serial.println("Altitud: " + String(gps.altitude.meters()));
  Serial.println("Satélites: " + String(gps.satellites.value()));
  Serial.println("Tiempo: " + String(gps.time.hour()) + ":" + String(gps.time.minute()) + ":" + String(gps.time.second()));
  if (millis() > 5000 && gps.charsProcessed() < 10)
  {
    Serial.println("El GPS no fue detectado. Comprueba la conexión de los cables.");
  }
  smartDelay(100);
}

// Función para leer datos de la humedad ambiental
float leerHumedadAmbiental(int n) {
  Serial.print("La humedad ambiental promedio es de: ");
  float hum = 0;
  for (int i = 0; i < n; i++) {
    hum += sensorHT.readHumidity();
    delay(8);
  }
  float humedad = hum / n;
  Serial.print(humedad);
  Serial.println("%");
  delay(30);
  return humedad;
}

// Función para leer datos de la temperatura
float leerTemperatura(int n) {
  Serial.print("La temperatura ambiental promedio es de: ");
  float temp = 0;
  for (int i = 0; i < n; i++) {
    temp += sensorHT.readTemperature();
    delay(8);
  }
  float temperatura = temp/n;
  Serial.print(temperatura);
  Serial.println(" °C");
  delay(30);
  return temperatura;
}

// Función para leer datos de la luz
float leerLuz(int n) {
  Serial.print("La luz promedio es de: ");
  float luz = 0;
  for (int i = 0; i < n; i++) {
    luz += aps.getAmbientLight();
    delay(13);
  }
  float luzAmbiente = luz / n;
  Serial.print(luzAmbiente);
  Serial.println(" lux");
  delay(30);
  return luzAmbiente;
}

// Función para leer datos de la proximidad
float leerProximidad(int n) {
  Serial.print("La proximidad promedio es de: ");
  float prox = 0;
  for (int i = 0; i < n; i++) {
    prox += aps.getProximity();
    delay(13);
  }
  float proximidad = prox / n;
  Serial.print(proximidad);
  Serial.println(" mm");
  delay(30);
  return proximidad;
}

// Función para leer datos de la humedad de la planta
float leerHumedadPlanta(int n) {
  Serial.print("La humedad de la planta promedio es de: ");
  float hum = 0;
  for (int i = 0; i < n; i++) {
    hum += analogRead(moisturePin);
    delay(8);
  }
  float humedadPlanta = hum / n;
  float porcentaje = map(humedadPlanta, 870, 800, 0, 100);
  porcentaje = constrain(porcentaje, 0, 100);
  Serial.print(porcentaje);
  Serial.println("%");
  if ((porcentaje >= 0 && porcentaje < 50) || (porcentaje > 70 && porcentaje <= 100)) {
    digitalWrite(ledPin, LOW); // Turn on LED if within the specified ranges
  } else {
    digitalWrite(ledPin, HIGH); // Turn off LED if outside the specified ranges
  }
  delay(30);
  return porcentaje;
}