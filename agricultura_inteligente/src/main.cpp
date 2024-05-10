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
void send_data(const char* id, float temperatura, float humedad, float latitud, float longitud);
void leerGPS(void);
float leerH(void);
float leerT(void);
float prunningH(int n);
float prunningT(int n);
float readMoisture(void);
long alsValue;
long psValue;
static const uint32_t GPSBaud = 9600;
const char* server = "18.212.13.195";
const char* ssid = "UPBWiFi";
const char* id = "point06";
int estado = 0;
const int prunning = 10;
float temperatura, humedad, latitud, longitud;
int moisturePin = 33;
float moistureLevel;

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
  pinMode(moisturePin, INPUT);
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
  switch(estado) {
    case 1:
      Serial.println("1. Leyendo datos del sensor de Humedad y Temperatura");
      temperatura = leerT();
      humedad = leerH();
      alsValue = aps.getAmbientLight();
	    psValue = aps.getProximity();
      Serial.print("Luz: ");
      Serial.print(alsValue);
      Serial.print(", Proximidad: ");
      Serial.println(psValue);
      moistureLevel = readMoisture();
      Serial.print("Soil Moisture: ");
      Serial.print(moistureLevel);
      estado = 2;
      break;
    case 2:
      Serial.println("2. Leyendo datos del GPS");
      leerGPS();
      estado = 3;
      break;
    case 3:
      Serial.println("3. Enviando datos al servidor");
      send_data(id, temperatura, humedad, latitud, longitud);
      estado = 4;
      break;
    case 4:
      Serial.println("4. Durmiendo");
      delay(10000);
      estado = 1;
      break;
    default:
      Serial.println("No capturo estados");
      delay(1000);
      break;
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
void send_data(const char* id, float temperatura, float humedad, float latitud, float longitud) {
  doc["id"] = String(id);
  doc["lat"] = latitud;
  doc["lon"] = longitud;
  doc["temperatura"] = temperatura;
  doc["humedad"] = humedad;
  String postData;
  serializeJson(doc, postData);

  if (client.connect(server, 80)) {
    Serial.println("Conectado al servidor");
    client.println("POST /update_data HTTP/1.1");
    client.println("Host: " + String(server));
    client.println("Content-Type: application/json");
    client.println("Content-Length: " + String(postData.length()));
    client.println();
    client.println(postData);
    Serial.println(postData);
  }
  else {
    Serial.println("Fallo al conectar al servidor");
  }
  delay(500);
  while (client.available()) {
    String line = client.readStringUntil('\n');
    Serial.println(line);
  }
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

// Función para leer datos de la humedad
float leerH() {
  Serial.println("Se va a leer la humedad");
  Serial.print("La humedad promedio es de: ");
  float humedad = prunningH(10);
  Serial.print(humedad);
  Serial.println("%");
  delay(30);
  return humedad;
}

// Función para leer datos de la temperatura
float leerT() {
  Serial.println("Se va a leer la temperatura");
  Serial.print("La temperatura promedio es de: ");
  float temperatura = prunningT(10);
  Serial.print(temperatura);
  Serial.println(" °C");
  delay(30);
  return temperatura;
}

// Función prunning humedad
float prunningH(int n) {
  float hum = 0;
  for (int i = 0; i < n; i++) {
    hum += sensorHT.readHumidity();
    delay(8);
  }
  return hum / n;
}

// Función prunning temperatura
float prunningT(int n) {
  float temp = 0;
  for (int i = 0; i < n; i++) {
    temp += sensorHT.readTemperature();
    delay(8);
  }
  return temp / n;
}

float readMoisture() {
  int sensorVal = analogRead(moisturePin);
  return 100.00 - ((sensorVal / 4095.00) * 100.00);
}