#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <esp_wifi.h>
#include <DHT.h>

// Wi-Fi 網路設定
const char* WIFI_SSID = "KSUProject";
// const char* WIFI_PASSWORD = "你的密碼"; // 若需要密碼請取消註釋

// TCP 伺服器設定
const char* TCP_SERVER_IP = "10.0.100.1";
const int TCP_SERVER_PORT = 5100;
const char* CLIENT_NAME = "NodeMCU-32S";

WiFiClient tcpClient;
SemaphoreHandle_t tcpMutex;

// 腳位設定
const uint8_t I2C_SDA = 21;
const uint8_t I2C_SCL = 22;
const uint8_t PIN_LIGHT_1 = 12;
const uint8_t PIN_LIGHT_2 = 14;
const uint8_t PIN_LIGHT_3 = 27;
const uint8_t DHTPIN = 25;
const uint8_t SOIL_PIN = 36;  // ADC1_0 (GPIO 36)

// 感測器常數與設定
const uint8_t BH1750_ADDRESS = 0x23;
const uint8_t BMP180_ADDRESS = 0x77;
const uint8_t DHTTYPE = DHT22;
DHT dht(DHTPIN, DHTTYPE);

// 土壤濕度校正數值 (請依實際環境調整)
const uint16_t DRY_VALUE = 4095;
const uint16_t WET_VALUE = 1500;

// BMP180 校正參數
int16_t ac1, ac2, ac3, b1, b2, mb, mc, md;
uint16_t ac4, ac5, ac6;

// 函數原型宣告
void readBmp180CalibrationParams();
double readBh1750Lux();
void readBmp180Data(double& temperature, int32_t& pressure);
void setupWiFi();
void ensureTcpConnection();
void sendTcpData(const char* id, double value);
void handleTcpCommands();

// FreeRTOS 感測器量測任務
void sensorTask(void* pvParameters) {
  TickType_t xLastWakeTime;
  const TickType_t xFrequency = pdMS_TO_TICKS(5000);  // 5 秒週期

  xLastWakeTime = xTaskGetTickCount();

  for (;;) {
    vTaskDelayUntil(&xLastWakeTime, xFrequency);

    // 1. 讀取光照度 (BH1750)
    double lux = readBh1750Lux();

    // 2. 讀取氣壓 (BMP180)
    double bmp_temp = 0.0;
    int32_t pressure = 0;
    readBmp180Data(bmp_temp, pressure);

    // 3. 讀取溫濕度 (AM2302 / DHT22)
    float humidity = dht.readHumidity();
    float am2302_temp = dht.readTemperature();
    double final_temp = 0.0;

    if (isnan(humidity) || isnan(am2302_temp)) {
      Serial.println("無法從 AM2302 感測器讀取資料！");
      humidity = 0.0f;
      final_temp = bmp_temp;  // 失敗時退回使用 BMP180 溫度
    } else {
      final_temp = (double)am2302_temp;
    }

    // 4. 讀取土壤濕度 (HD-38)
    uint16_t soilRaw = analogRead(SOIL_PIN);
    int16_t soilPercent = map(soilRaw, DRY_VALUE, WET_VALUE, 0, 100);
    soilPercent = constrain(soilPercent, 0, 100);

    // 序列埠監控輸出
    Serial.printf("照度: %.2f lx, 溫度: %.1f °C, 濕度: %.1f %%, 氣壓: %d Pa, 土壤濕度: %d%%\n",
                  lux, final_temp, humidity, pressure, soilPercent);

    // 透過 TCP 傳送至伺服器
    sendTcpData("NodeMCU-32S_lux", lux);
    sendTcpData("NodeMCU-32S_temperature", final_temp);
    sendTcpData("NodeMCU-32S_humidity", (double)humidity);
    sendTcpData("NodeMCU-32S_pressure", (double)pressure);
    sendTcpData("NodeMCU-32S_soil", (double)soilPercent);

    if ((xTaskGetTickCount() - xLastWakeTime) > xFrequency) {
      xLastWakeTime = xTaskGetTickCount();
    }
  }
}

void setup() {
  Serial.begin(115200);

  // 初始化 GPIO 與 ADC
  pinMode(PIN_LIGHT_1, OUTPUT);
  digitalWrite(PIN_LIGHT_1, HIGH);
  pinMode(PIN_LIGHT_2, OUTPUT);
  digitalWrite(PIN_LIGHT_2, HIGH);
  pinMode(PIN_LIGHT_3, OUTPUT);
  digitalWrite(PIN_LIGHT_3, HIGH);

  analogReadResolution(12);  // 設定 ADC 解析度為 12 位元

  tcpMutex = xSemaphoreCreateMutex();

  setupWiFi();

  Wire.begin(I2C_SDA, I2C_SCL);
  delay(100);

  dht.begin();
  readBmp180CalibrationParams();

  Serial.println("感測器初始化完成。");

  // 建立 FreeRTOS 任務
  xTaskCreate(sensorTask, "SensorTask", 8192, NULL, 1, NULL);
}

void loop() {
  handleTcpCommands();
  delay(50);
}

#pragma region 網路通訊與 TCP 邏輯

void setupWiFi() {
  int8_t attempts = 0;
  Serial.println("\n正在初始化 Wi-Fi 連線...");
  WiFi.mode(WIFI_STA);
  WiFi.disconnect(true, true);
  delay(500);
  WiFi.begin(WIFI_SSID);

  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\nWi-Fi 連線成功！裝置 IP: %s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("\nWi-Fi 連線失敗！");
  }
}

void ensureTcpConnection() {
  if (WiFi.status() != WL_CONNECTED) return;

  if (!tcpClient.connected()) {
    static unsigned long lastReconnectAttempt = 0;
    if (millis() - lastReconnectAttempt < 5000) return;
    lastReconnectAttempt = millis();

    tcpClient.stop();
    if (tcpClient.connect(TCP_SERVER_IP, TCP_SERVER_PORT)) {
      Serial.println("TCP 連線成功，發送註冊訊息...");
      char payload[256];
      snprintf(payload, sizeof(payload),
               "{\"action\":\"register\",\"name\":\"%s\",\"gpios\":[{\"pin\":%d,\"name\":\"Light 1\"},{\"pin\":%d,\"name\":\"Light 2\"},{\"pin\":%d,\"name\":\"Light 3\"}]}\n",
               CLIENT_NAME, PIN_LIGHT_1, PIN_LIGHT_2, PIN_LIGHT_3);
      tcpClient.print(payload);
    }
  }
}

void sendTcpData(const char* id, double value) {
  if (xSemaphoreTake(tcpMutex, portMAX_DELAY)) {
    ensureTcpConnection();
    if (tcpClient.connected()) {
      char payload[128];
      snprintf(payload, sizeof(payload), "{\"action\":\"post\",\"id\":\"%s\",\"value\":%.2f}\n", id, value);
      tcpClient.print(payload);
    }
    xSemaphoreGive(tcpMutex);
  }
}

void handleTcpCommands() {
  if (xSemaphoreTake(tcpMutex, portMAX_DELAY)) {
    ensureTcpConnection();
    while (tcpClient.available()) {
      String line = tcpClient.readStringUntil('\n');
      line.trim();
      if (line.length() == 0) continue;

      if (line.indexOf("\"action\":\"set_gpio\"") >= 0) {
        int16_t pin = -1;
        bool state = false;
        int16_t pinIndex = line.indexOf("\"pin\":");
        if (pinIndex > 0) pin = line.substring(pinIndex + 6).toInt();
        int16_t stateIndex = line.indexOf("\"state\":");
        if (stateIndex > 0) state = line.substring(stateIndex + 8).startsWith("true");

        if (pin == PIN_LIGHT_1 || pin == PIN_LIGHT_2 || pin == PIN_LIGHT_3) {
          digitalWrite(pin, state ? LOW : HIGH);
          Serial.printf("TCP 指令: 設定 GPIO %d 為 %s\n", pin, state ? "LOW" : "HIGH");
        }
      } else if (line.indexOf("\"action\":\"get_gpio\"") >= 0) {
        int16_t pin = -1;
        int16_t pinIndex = line.indexOf("\"pin\":");
        if (pinIndex > 0) pin = line.substring(pinIndex + 6).toInt();

        if (pin == PIN_LIGHT_1 || pin == PIN_LIGHT_2 || pin == PIN_LIGHT_3) {
          bool state = (digitalRead(pin) == LOW);
          char payload[128];
          snprintf(payload, sizeof(payload), "{\"action\":\"gpio_state\",\"pin\":%d,\"state\":%s}\n", pin, state ? "true" : "false");
          tcpClient.print(payload);
        }
      }
    }
    xSemaphoreGive(tcpMutex);
  }
}

#pragma endregion

#pragma region 各感測器讀取邏輯(BH1750, BMP180)

double readBh1750Lux() {
  Wire.beginTransmission(BH1750_ADDRESS);
  Wire.write(0x10);
  Wire.endTransmission();
  delay(200);
  Wire.requestFrom(BH1750_ADDRESS, (uint8_t)2);
  if (Wire.available() >= 2) {
    uint16_t rawValue = (Wire.read() << 8) | Wire.read();
    return rawValue / 1.2;
  }
  return 0.0;
}

int16_t readBmp180S16(uint8_t reg) {
  Wire.beginTransmission(BMP180_ADDRESS);
  Wire.write(reg);
  Wire.endTransmission();
  Wire.requestFrom(BMP180_ADDRESS, (uint8_t)2);
  return (Wire.available() >= 2) ? (Wire.read() << 8) | Wire.read() : 0;
}

uint16_t readBmp180U16(uint8_t reg) {
  Wire.beginTransmission(BMP180_ADDRESS);
  Wire.write(reg);
  Wire.endTransmission();
  Wire.requestFrom(BMP180_ADDRESS, (uint8_t)2);
  return (Wire.available() >= 2) ? (Wire.read() << 8) | Wire.read() : 0;
}

void readBmp180CalibrationParams() {
  ac1 = readBmp180S16(0xAA);
  ac2 = readBmp180S16(0xAC);
  ac3 = readBmp180S16(0xAE);
  ac4 = readBmp180U16(0xB0);
  ac5 = readBmp180U16(0xB2);
  ac6 = readBmp180U16(0xB4);
  b1 = readBmp180S16(0xB6);
  b2 = readBmp180S16(0xB8);
  mb = readBmp180S16(0xBA);
  mc = readBmp180S16(0xBC);
  md = readBmp180S16(0xBE);
}

void readBmp180Data(double& temperature, int32_t& pressure) {
  int oss = 0;
  Wire.beginTransmission(BMP180_ADDRESS);
  Wire.write(0xF4);
  Wire.write(0x2E);
  Wire.endTransmission();
  delay(5);
  int32_t ut = readBmp180S16(0xF6);

  Wire.beginTransmission(BMP180_ADDRESS);
  Wire.write(0xF4);
  Wire.write(0x34 + (oss << 6));
  Wire.endTransmission();
  delay(5);

  Wire.beginTransmission(BMP180_ADDRESS);
  Wire.write(0xF6);
  Wire.endTransmission();
  Wire.requestFrom(BMP180_ADDRESS, (uint8_t)3);
  int32_t up = 0;
  if (Wire.available() >= 3) {
    up = ((Wire.read() << 16) + (Wire.read() << 8) + Wire.read()) >> (8 - oss);
  }

  int32_t x1 = ((ut - ac6) * ac5) >> 15;
  int32_t x2 = (mc << 11) / (x1 + md);
  int32_t b5 = x1 + x2;
  temperature = ((b5 + 8) >> 4) / 10.0;

  int32_t b6 = b5 - 4000;
  int32_t x1_p = (b2 * ((b6 * b6) >> 12)) >> 11;
  int32_t x2_p = (ac2 * b6) >> 11;
  int32_t x3_p = x1_p + x2_p;
  int32_t b3 = (((ac1 * 4 + x3_p) << oss) + 2) >> 2;
  x1_p = (ac3 * b6) >> 13;
  x2_p = (b1 * ((b6 * b6) >> 12)) >> 16;
  x3_p = ((x1_p + x2_p) + 2) >> 2;
  uint32_t b4 = (ac4 * (uint32_t)(x3_p + 32768)) >> 15;
  int32_t b7 = (up - b3) * (50000 >> oss);
  int32_t p = (b7 < 0x80000000) ? (b7 * 2) / b4 : (b7 / b4) * 2;
  x1_p = (p >> 8) * (p >> 8);
  x1_p = (x1_p * 3038) >> 16;
  x2_p = (-7357 * p) >> 16;
  pressure = p + ((x1_p + x2_p + 3791) >> 4);
}

#pragma endregion