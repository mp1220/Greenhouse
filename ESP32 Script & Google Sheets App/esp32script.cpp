#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <ArduinoJson.h>
#include <ArduinoOTA.h>
#include <math.h>
#include <Preferences.h>

#include <Adafruit_SHT4x.h>
#include <Adafruit_APDS9960.h>
#include <Adafruit_TSL2591.h>

#define FIRMWARE_VERSION "1.0.0"

// ===================== WIFI + MQTT =====================

const char* ssid        = "MyAltice 2b8a09";
const char* password    = "orchid-734-107";
const char* mqtt_server = "192.168.1.163";

WiFiClient espClient;
PubSubClient mqttClient(espClient);

const char* TOPIC_SENSORS       = "greenhouse/sensors";
const char* TOPIC_COMMANDS      = "greenhouse/commands";
const char* TOPIC_JETSON_STATUS = "greenhouse/jetson/status";
const char* TOPIC_ESP_STATUS    = "greenhouse/esp32/status";

// ===================== PINS + PWM =====================

const int I2C_SDA_PIN = 21;
const int I2C_SCL_PIN = 22;

const int CIRC_FAN_PIN = 25;
const int LIGHT_PIN    = 26;
const int EXH_FAN_PIN  = 27;

const int CIRC_CH  = 0;
const int LIGHT_CH = 1;
const int EXH_CH   = 2;

const int PWM_FREQ = 25000;
const int PWM_RES  = 8;

// ===================== SENSORS =====================

Adafruit_SHT4x sht4;
Adafruit_APDS9960 apds;
Adafruit_TSL2591 tsl(2591);

bool sht4_ok = false;
bool apds_ok = false;
bool tsl_ok  = false;

// ===================== STATE =====================

uint8_t circ_pwm  = 0;
uint8_t light_pwm = 0;
uint8_t exh_pwm   = 0;

Preferences prefs;
int mqttReconnects = 0;

// ===================== HELPERS =====================

float dewPointF(float c, float rh) {
  float g = (17.62f * c) / (243.12f + c) + logf(rh / 100.0f);
  return ((243.12f * g) / (17.62f - g)) * 9.0f / 5.0f + 32.0f;
}

float vpdKpa(float c, float rh) {
  float svp = 0.6108f * expf((17.27f * c) / (c + 237.3f));
  return fmaxf(0.0f, svp * (1.0f - rh / 100.0f));
}

// ===================== COMMANDS =====================

void applyCirc(uint8_t v) {
  circ_pwm = v;
  ledcWrite(CIRC_CH, v);
  prefs.putUInt("circ", v);
}

void applyLight(uint8_t v) {
  light_pwm = v;
  ledcWrite(LIGHT_CH, v);
  prefs.putUInt("light", v);
}

void applyExh(uint8_t v) {
  exh_pwm = v;
  ledcWrite(EXH_CH, v);
  prefs.putUInt("exh", v);
}

void mqttCallback(char* topic, byte* payload, unsigned int len) {
  StaticJsonDocument<256> doc;
  if (deserializeJson(doc, payload, len)) return;

  if (doc.containsKey("circulation_fan_pwm")) {
    int v = doc["circulation_fan_pwm"].as<int>();
    applyCirc(constrain(v, 0, 255));
  }

  if (doc.containsKey("grow_light_pwm")) {
    int v = doc["grow_light_pwm"].as<int>();
    applyLight(constrain(v, 0, 255));
  }

  if (doc.containsKey("exhaust_fan_pwm")) {
    int v = doc["exhaust_fan_pwm"].as<int>();
    applyExh(constrain(v, 0, 255));
  }
}

// ===================== MQTT =====================

void connectMQTT() {
  mqttClient.setServer(mqtt_server, 1883);
  mqttClient.setCallback(mqttCallback);
  mqttClient.setBufferSize(512);

  mqttReconnects++;
  if (mqttClient.connect("ESP32-Greenhouse",
                          TOPIC_ESP_STATUS,
                          1,
                          true,
                          "{\"status\":\"offline\"}")) {
    mqttClient.publish(TOPIC_ESP_STATUS, "{\"status\":\"online\"}", true);
    mqttClient.subscribe(TOPIC_COMMANDS);
    mqttClient.subscribe(TOPIC_JETSON_STATUS);
  }
}

// ===================== SENSOR PUBLISH =====================

void publishSensorData() {
  StaticJsonDocument<512> doc;

  doc["sensor_sht4_ok"] = sht4_ok;
  doc["sensor_apds_ok"] = apds_ok;
  doc["sensor_tsl_ok"]  = tsl_ok;

  if (sht4_ok) {
    sensors_event_t h, t;
    if (sht4.getEvent(&h, &t)) {
      float tf = t.temperature * 9.0f / 5.0f + 32.0f;
      doc["inside_temp_f"]      = tf;
      doc["inside_humidity_rh"] = h.relative_humidity;
      doc["inside_dew_point_f"] = dewPointF(t.temperature, h.relative_humidity);
      doc["inside_vpd_kpa"]     = vpdKpa(t.temperature, h.relative_humidity);
    } else {
      Serial.println("ERROR: SHT4x read failed");
    }
  }

  if (tsl_ok) {
    uint32_t fs = tsl.getFullLuminosity();
    uint16_t ir = fs & 0xFFFF;
    uint16_t full = fs >> 16;
    uint32_t lux = tsl.calculateLux(full, ir);

    doc["inside_brightness_lux"] = lux;
    doc["tsl_full_spectrum"]     = full;
    doc["tsl_infrared"]          = ir;
  }

  if (apds_ok && apds.colorDataReady()) {
    uint16_t r, g, b, c;
    apds.getColorData(&r, &g, &b, &c);
    doc["outside_brightness_raw"] = c;
    doc["outside_color_r"] = r;
    doc["outside_color_g"] = g;
    doc["outside_color_b"] = b;
  }

  doc["circulation_fan_pwm"] = circ_pwm;
  doc["grow_light_pwm"]      = light_pwm;
  doc["exhaust_fan_pwm"]     = exh_pwm;

  doc["esp32_runtime_ms"] = millis();
  doc["firmware_version"] = FIRMWARE_VERSION;
  doc["wifi_rssi"]        = WiFi.RSSI();
  doc["mqtt_reconnects"]  = mqttReconnects;

  char buf[512];
  size_t n = serializeJson(doc, buf);
  mqttClient.publish(TOPIC_SENSORS, buf, n);
}

// ===================== SETUP =====================

void setup() {
  Serial.begin(115200);
  prefs.begin("gh", false);

  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);

  ledcSetup(CIRC_CH, PWM_FREQ, PWM_RES);
  ledcSetup(LIGHT_CH, PWM_FREQ, PWM_RES);
  ledcSetup(EXH_CH, PWM_FREQ, PWM_RES);

  ledcAttachPin(CIRC_FAN_PIN, CIRC_CH);
  ledcAttachPin(LIGHT_PIN, LIGHT_CH);
  ledcAttachPin(EXH_FAN_PIN, EXH_CH);

  circ_pwm  = prefs.getUInt("circ", 0);
  light_pwm = prefs.getUInt("light", 0);
  exh_pwm   = prefs.getUInt("exh", 0);

  applyCirc(circ_pwm);
  applyLight(light_pwm);
  applyExh(exh_pwm);

  sht4_ok = sht4.begin();
  if (sht4_ok) {
    sht4.setPrecision(SHT4X_HIGH_PRECISION);
    Serial.println("SHT4x initialized");
  } else {
    Serial.println("ERROR: SHT4x not found");
  }

  apds_ok = apds.begin();
  if (apds_ok) {
    apds.enableColor(true);
    Serial.println("APDS9960 initialized");
  } else {
    Serial.println("ERROR: APDS9960 not found");
  }

  tsl_ok = tsl.begin();
  if (tsl_ok) {
    tsl.setGain(TSL2591_GAIN_MED);
    tsl.setTiming(TSL2591_INTEGRATIONTIME_300MS);
    Serial.println("TSL2591 initialized");
  } else {
    Serial.println("ERROR: TSL2591 not found");
  }

  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(200);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  ArduinoOTA.begin();
  connectMQTT();
}

// ===================== LOOP =====================

unsigned long lastPub = 0;

void loop() {
  ArduinoOTA.handle();

  if (!mqttClient.connected()) connectMQTT();
  mqttClient.loop();

  if (millis() - lastPub > 5000) {
    lastPub = millis();
    publishSensorData();
  }
}
