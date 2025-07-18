#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// Configuración OLED
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// Configuración pines
const int mq3Pin = 34;
const int ledRojo = 25;
const int ledVerde = 26;
const int botonPin = 14;          // Pin del botón para envío manual
const int valorMinimo = 0;
const int valorMaximo = 3500;
const float umbralLegal = 0.55;

// Configuración WiFi
const char* ssid = "TU_SSID";
const char* password = "TU_PASSWORD";
const char* serverUrl = "http://TU_IP_FLASK:5000/datos";

// Variables para manejo de tiempo
unsigned long lastSendTime = 0;
const long sendInterval = 60000;  // 60 segundos (1 minuto)

// Variables para manejo de botón
bool botonPresionado = false;
unsigned long lastDebounceTime = 0;
const long debounceDelay = 50;    // Tiempo anti-rebote

void setup() {
  // Inicializar pines
  pinMode(mq3Pin, INPUT);
  pinMode(ledRojo, OUTPUT);
  pinMode(ledVerde, OUTPUT);
  pinMode(botonPin, INPUT_PULLUP);  // Botón con resistencia pull-up
  Serial.begin(115200);

  // Inicializar OLED
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("Error al iniciar OLED"));
    while (true);
  }

  // Mostrar pantalla de inicio
  mostrarMensajeInicial();

  // Conectar a WiFi
  conectarWiFi();
}

void loop() {
  // Leer sensor y calcular concentración
  int valorSensor = analogRead(mq3Pin);
  float concentracionMgL = calcularConcentracion(valorSensor);

  // Controlar LEDs según el nivel
  controlarLEDs(concentracionMgL);

  // Mostrar datos en Serial Monitor
  mostrarDatosSerial(valorSensor, concentracionMgL);

  // Mostrar datos en pantalla OLED
  mostrarDatosOLED(concentracionMgL);

  // Manejar botón para envío manual
  int lecturaBoton = digitalRead(botonPin);
  
  // Detectar flanco descendente (botón presionado)
  if (lecturaBoton == LOW && !botonPresionado) {
    if (millis() - lastDebounceTime > debounceDelay) {
      botonPresionado = true;
      lastDebounceTime = millis();
      
      // Forzar envío inmediato
      enviarDatosServidor(valorSensor, concentracionMgL);
      mostrarMensajeBoton();  // Feedback visual
    }
  }
  
  // Resetear estado cuando se suelta el botón
  if (lecturaBoton == HIGH && botonPresionado) {
    botonPresionado = false;
  }

  // Envío automático cada minuto
  unsigned long currentTime = millis();
  if (currentTime - lastSendTime >= sendInterval) {
    enviarDatosServidor(valorSensor, concentracionMgL);
    lastSendTime = currentTime;
  }

  delay(100);
}

// ========== FUNCIONES AUXILIARES ==========

// Función para mostrar mensaje inicial en OLED
void mostrarMensajeInicial() {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.println("  Medidor Alcohol");
  display.println("  0-2 mg/L BAC");
  display.println("-------------------");
  display.println(" Boton: Envio MANUAL");
  display.println(" Auto: 60 segundos");
  display.display();
  delay(2000);
}

// Función para conectar a WiFi
void conectarWiFi() {
  display.clearDisplay();
  display.setCursor(0, 0);
  display.println(" Conectando WiFi...");
  display.display();

  WiFi.begin(ssid, password);

  int intentos = 0;
  while (WiFi.status() != WL_CONNECTED && intentos < 20) {
    delay(500);
    Serial.print(".");
    display.print(".");
    display.display();
    intentos++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi conectado");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());

    display.clearDisplay();
    display.setCursor(0, 0);
    display.println("  WiFi Conectado");
    display.println("-------------------");
    display.print("SSID: ");
    display.println(ssid);
    display.print("IP: ");
    display.println(WiFi.localIP());
    display.display();
    delay(2000);
  } else {
    Serial.println("Fallo en conexión WiFi");
    display.clearDisplay();
    display.setCursor(0, 0);
    display.println(" Error WiFi");
    display.println("-------------------");
    display.println("No se pudo conectar");
    display.println("Reiniciando...");
    display.display();
    delay(3000);
    ESP.restart();
  }
}

// Calcular concentración de alcohol
float calcularConcentracion(int valorSensor) {
  // Calcular concentración en mg/L (0-2 mg/L)
  float concentracionMgL = ((float)(valorSensor - valorMinimo) / (valorMaximo - valorMinimo)) * 2.0;
  // Limitar el rango entre 0 y 2.0
  return constrain(concentracionMgL, 0, 2.0);
}

// Controlar LEDs según concentración
void controlarLEDs(float concentracionMgL) {
  if (concentracionMgL > umbralLegal) {
    digitalWrite(ledRojo, HIGH);
    digitalWrite(ledVerde, LOW);
  } else {
    digitalWrite(ledRojo, LOW);
    digitalWrite(ledVerde, HIGH);
  }
}

// Mostrar datos en Serial Monitor
void mostrarDatosSerial(int valorSensor, float concentracionMgL) {
  Serial.print("Sensor: ");
  Serial.print(valorSensor);
  Serial.print(" - BAC: ");
  Serial.print(concentracionMgL, 2);
  Serial.println(" mg/L");
}

// Mostrar datos en pantalla OLED
void mostrarDatosOLED(float concentracionMgL) {
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("Nivel de Alcohol");
  display.drawLine(0, 10, 128, 10, SSD1306_WHITE);

  display.setTextSize(2);
  display.setCursor(0, 15);
  display.print(concentracionMgL, 2);
  display.println(" mg/L");

  display.setTextSize(1);
  display.setCursor(0, 35);
  if (concentracionMgL > umbralLegal) {
    display.println("ESTADO: PELIGROSO");
    display.println("Excede limite legal");
  } else {
    display.println("ESTADO: NORMAL");
    display.println("Dentro del limite");
  }

  // Barra de progreso
  int barWidth = map(concentracionMgL * 100, 0, 200, 0, 120);
  display.drawRect(0, 55, 120, 8, SSD1306_WHITE);
  display.fillRect(0, 55, barWidth, 8, SSD1306_WHITE);
  
  // Línea de umbral legal
  int thresholdPos = map(umbralLegal * 100, 0, 200, 0, 120);
  display.drawLine(thresholdPos, 55, thresholdPos, 63, SSD1306_BLACK);

  display.display();
}

// Enviar datos al servidor Flask
void enviarDatosServidor(int valorSensor, float concentracionMgL) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi desconectado - Reconectando...");
    conectarWiFi();
    return;
  }

  HTTPClient http;
  http.begin(serverUrl);
  http.addHeader("Content-Type", "application/x-www-form-urlencoded");
  
  // Construir datos para enviar (formato requerido por Flask)
  String postData = "sensor_id=1"; // ID fijo del sensor
  postData += "&valor=" + String(valorSensor);
  postData += "&concentracion=" + String(concentracionMgL, 2);
  
  Serial.println("Enviando datos a servidor...");
  Serial.println("URL: " + String(serverUrl));
  Serial.println("Datos: " + postData);

  int httpCode = http.POST(postData);

  // Mostrar estado en OLED
  display.fillRect(0, 45, 128, 10, SSD1306_BLACK); // Limpiar área
  display.setTextSize(1);
  display.setCursor(0, 45);
  
  if (httpCode > 0) {
    Serial.printf("Código HTTP: %d\n", httpCode);
    display.print("HTTP: ");
    display.print(httpCode);
    
    if (httpCode == HTTP_CODE_OK) {
      String payload = http.getString();
      Serial.println("Respuesta: " + payload);
      display.println(" OK");
    }
  } else {
    Serial.printf("Error en POST: %s\n", http.errorToString(httpCode).c_str());
    display.print("Error: ");
    display.println(http.errorToString(httpCode).substring(0, 10)); // Mostrar primeros 10 caracteres
  }
  
  display.display();
  http.end();
}

// Función para mostrar confirmación de envío manual
void mostrarMensajeBoton() {
  display.fillRect(0, 45, 128, 10, SSD1306_BLACK);
  display.setTextSize(1);
  display.setCursor(0, 45);
  display.println("ENVIO MANUAL");
  display.display();
  delay(1500);  // Mostrar mensaje por 1.5 segundos
}
