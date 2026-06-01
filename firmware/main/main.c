#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "esp_netif.h"
#include "esp_event.h"
#include "esp_wifi.h"
#include "mqtt_client.h"

#define WIFI_SSID       "NOME_DA_SUA_REDE_WIFI"
#define WIFI_PASS       "SENHA_DA_REDE"
#define BROKER_URL      "mqtt://192.168.56.1"

#define PIR_SENSOR_PIN    2 // Entrada: Sensor de movimento HC-SR501
#define LIGHT_SENSOR_PIN  3 // Entrada: Sensor de luminosidade LDR
#define RELAY_LIGHT_PIN   4 // Saída: Relé de Iluminação

static const char *TAG = "SISTEMA_EDGE";
esp_mqtt_client_handle_t client = NULL;

static void wifi_init_sta(void) {
    esp_netif_init();
    esp_event_loop_create_default();
    esp_netif_create_default_wifi_sta();
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);

    wifi_config_t wifi_config = {
        .sta = {
            .ssid = WIFI_SSID,
            .password = WIFI_PASS,
        },
    };
    esp_wifi_set_mode(WIFI_MODE_STA);
    esp_wifi_set_config(WIFI_IF_STA, &wifi_config);
    esp_wifi_start();
    esp_wifi_connect();
    ESP_LOGI(TAG, "Conectando ao WiFi...");
}

static void mqtt_app_start(void) {
    esp_mqtt_client_config_t mqtt_cfg = {
        .broker.address.uri = BROKER_URL,
    };
    client = esp_mqtt_client_init(&mqtt_cfg);
    esp_mqtt_client_start(client);
    ESP_LOGI(TAG, "Conectando ao Broker MQTT...");
}

void iniciar_gpios() {
    gpio_reset_pin(RELAY_LIGHT_PIN);
    gpio_set_direction(RELAY_LIGHT_PIN, GPIO_MODE_OUTPUT);
    
    gpio_reset_pin(PIR_SENSOR_PIN);
    gpio_set_direction(PIR_SENSOR_PIN, GPIO_MODE_INPUT);
    gpio_set_pull_mode(PIR_SENSOR_PIN, GPIO_PULLDOWN_ONLY);

    gpio_reset_pin(LIGHT_SENSOR_PIN);
    gpio_set_direction(LIGHT_SENSOR_PIN, GPIO_MODE_INPUT);
    gpio_set_pull_mode(LIGHT_SENSOR_PIN, GPIO_PULLDOWN_ONLY);

    ESP_LOGI(TAG, "GPIOs inicializados com sucesso.");
}

void app_main(void) {
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
      ESP_ERROR_CHECK(nvs_flash_erase());
      ret = nvs_flash_init();
    }
    
    iniciar_gpios();
    wifi_init_sta();
    vTaskDelay(pdMS_TO_TICKS(5000));
    mqtt_app_start();

    int ultimo_estado_movimento = -1;

    while (1) {
        int movimento    = gpio_get_level(PIR_SENSOR_PIN);
        int luminosidade = gpio_get_level(LIGHT_SENSOR_PIN);
        
        if (movimento != ultimo_estado_movimento) {
            ultimo_estado_movimento = movimento;

            if (movimento) {
                ESP_LOGI(TAG, "Movimento detectado!");
            } else if (luminosidade == 1 && !movimento) {
                ESP_LOGW(TAG, "Sala vazia...");
                gpio_set_level(RELAY_LIGHT_PIN, 0);
            }

            if (luminosidade) {
                ESP_LOGI(TAG, "Ambiente claro.");
            } else {
                ESP_LOGI(TAG, "Ambiente escuro.");
            }
        }

        vTaskDelay(pdMS_TO_TICKS(500));
    }
}