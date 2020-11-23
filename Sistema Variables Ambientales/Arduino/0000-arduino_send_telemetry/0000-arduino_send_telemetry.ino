#include <WiFi.h>
#include <ThingsBoard.h>
#include "DHT.h"
#include <Wire.h>    // I2C library
#include "iAQcore.h" // iAQ-Core driver

//Developed with ArduinoIDE
//Define WiFi Credentials
#define WIFI_AP             "SBC"
#define WIFI_PASSWORD       "sbc$2020"

//Define PIN Sensor's Number
#define DHTPIN 33     // what pin we're connected to
#define DHTTYPE DHT11   // DHT 11
#define AIRPIN 34
#define PIRPIN 32

//Define Thingsboard Instance Credentials
#define TOKEN "Mu3efPcxknpcnYMgTcih"
#define THINGSBOARD_SERVER "138.4.92.46"

DHT dht(DHTPIN, DHTTYPE);
WiFiClient client;
// Initialize ThingsBoard instance
ThingsBoard tb(client);
// the Wifi radio's status
int status = WL_IDLE_STATUS;    

iAQcore iaqcore;

#if defined(ARDUINO_ARCH_AVR)
#define debug  Serial

#elif defined(ARDUINO_ARCH_SAMD) ||  defined(ARDUINO_ARCH_SAM)
#define debug  SerialUSB
#else
#define debug  Serial
#endif


int air_value;
int sample_size=10;
unsigned long suma = 0;
unsigned long media;
int pir_value;
                
void setup() {
  
  // initialize serial for debugging
  Serial.begin(115200);

  delay(1000);
  pinMode(PIRPIN, INPUT);


    // We start by connecting to a WiFi network

    Serial.println();
    Serial.println();
    Serial.print("Connecting to ");
    Serial.println(WIFI_AP);

    WiFi.begin(WIFI_AP, WIFI_PASSWORD);

    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }

    Serial.println("");
    Serial.println("WiFi connected");
    Serial.println("IP address: ");
    Serial.println(WiFi.localIP());

    Wire.begin(21, 22);
    bool ok = iaqcore.begin();
  Serial.println(ok ? "iAQ-Core initialized" : "ERROR initializing iAQ-Core");

    dht.begin();
}



void loop() {



  if (status != WL_CONNECTED) {
    Serial.println("Connecting to AP ...");
    Serial.print("Attempting to connect to WPA SSID: ");
    Serial.println(WIFI_AP);
    // Connect to WPA/WPA2 network
    status = WiFi.begin(WIFI_AP, WIFI_PASSWORD);
    return;
  }

  while (!tb.connected()) {
    // Connect to the ThingsBoard
    Serial.print("Connecting to: ");
    Serial.print(THINGSBOARD_SERVER);
    Serial.print(" with token ");
    Serial.println(TOKEN);
    if (!tb.connect(THINGSBOARD_SERVER, TOKEN)) {
      Serial.println("Failed to connect");
      return;
    }
  }

  float temp_hum_val[2] = {0};
  // Reading temperature or humidity takes about 250 milliseconds!
  // Sensor readings may also be up to 2 seconds 'old' (its a very slow sensor)


  if (!dht.readTempAndHumidity(temp_hum_val)) {
    debug.print("Humidity: ");
    debug.print(temp_hum_val[0]);
    debug.print(" %\t");
    debug.print("Temperature: ");
    debug.print(temp_hum_val[1]);
    debug.println(" *C");
  } else {
    debug.println("Failed to get temprature and humidity value.");
  }

  for (int i=0; i<10; i++)
  {
    air_value=analogRead(AIRPIN); // conversion AN
    suma=suma+air_value; // somme de 10 échantillons
    media=suma/sample_size; // calcul de la moyenne de 10 échantillons
    delay(10);
  }
  suma=0;
  Serial.print("Air Value=");
  Serial.println(media);


    uint16_t eco2;
  uint16_t stat;
  uint32_t resist;
  uint16_t etvoc;
  iaqcore.read(&eco2, &stat, &resist, &etvoc);

  // Print
  if ( stat & IAQCORE_STAT_I2CERR ) {
    Serial.println("iAQcore: I2C error");
  } else if ( stat & IAQCORE_STAT_ERROR ) {
    Serial.println("iAQcore: chip broken");
  } else if ( stat & IAQCORE_STAT_BUSY ) {
    Serial.println("iAQcore: chip busy");
  } else {
    Serial.print("iAQcore: ");
    Serial.print("eco2=");    Serial.print(eco2);     Serial.print(" ppm,  ");
    Serial.print("tvoc=");    Serial.print(etvoc);    Serial.print(" ppb  ");
    Serial.print("(resist="); Serial.print(resist);   Serial.print(" ohm)  ");
    if ( stat & IAQCORE_STAT_RUNIN ) Serial.print(" RUNIN");
    Serial.println();
  }


  //PIR Block

  pir_value = digitalRead(PIRPIN);
  Serial.print("Pir status"); Serial.println(pir_value);

  Serial.println("Sending data...");

  // Uploads new telemetry to ThingsBoard using MQTT. 
  // See https://thingsboard.io/docs/reference/mqtt-api/#telemetry-upload-api 
  // for more details

  //DHT11
  tb.sendTelemetryFloat("Humidity", temp_hum_val[0]);
  tb.sendTelemetryFloat("Temp", temp_hum_val[1]);

  //MQ135
  tb.sendTelemetryInt("Valor Aire  ", air_value);
  tb.sendTelemetryInt("Media Aire", media);

  //IAQCore
  tb.sendTelemetryInt("eCO2 ppm", eco2);
  tb.sendTelemetryInt("tVoc ppb", etvoc);

  //PIR
  tb.sendTelemetryInt("PIR detection", pir_value);
  
  
  delay(1000); 
  
  
  
  tb.loop();
}
