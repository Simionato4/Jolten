#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "esp_netif.h"
#include "esp_event.h"
#include "esp_wifi.h"
#include "esp_timer.h"
#include "mqtt_client.h"

#define WIFI_SSID        "DW-ESCRITORIO"
#define WIFI_PASS        "dwluiz342"
#define BROKER_URL       "mqtt://192.168.0.13"
#define SALA_ID          "101"

#define PIR_SENSOR_PIN   2
#define RELAY_LIGHT_PIN  4
#define LDR_SENSOR_PIN   10

#define WIFI_CONNECTED_BIT BIT0

static const char *TAG = "SISTEMA_EDGE";
static esp_mqtt_client_handle_t client = NULL;
static EventGroupHandle_t s_wifi_event_group;
static esp_netif_t *s_netif = NULL;

// --- WiFi ---

static void wifi_event_handler(void *arg, esp_event_base_t base, int32_t id, void *data) {
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
        ESP_LOGW(TAG, "WiFi desconectado. Reconectando...");
        esp_wifi_connect();
    } else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *event = (ip_event_got_ip_t *) data;
        ESP_LOGI(TAG, "✅ WiFi conectado! IP: " IPSTR, IP2STR(&event->ip_info.ip));
        xEventGroupSetBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
    }
}

static void wifi_init_sta(void) {
    s_wifi_event_group = xEventGroupCreate();
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    s_netif = esp_netif_create_default_wifi_sta();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    esp_event_handler_instance_register(WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler, NULL, NULL);
    esp_event_handler_instance_register(IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler, NULL, NULL);

    wifi_config_t wifi_config = { .sta = { .ssid = WIFI_SSID, .password = WIFI_PASS } };
    wifi_country_t country = { .cc = "BR", .schan = 1, .nchan = 13, .policy = WIFI_COUNTRY_POLICY_MANUAL };

    ESP_ERROR_CHECK(esp_wifi_set_country(&country));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());

    ESP_LOGI(TAG, "Aguardando WiFi...");
    xEventGroupWaitBits(s_wifi_event_group, WIFI_CONNECTED_BIT, pdFALSE, pdFALSE, pdMS_TO_TICKS(20000));
}

// --- MQTT ---

static void mqtt_event_handler(void *arg, esp_event_base_t base, int32_t id, void *data) {
    esp_mqtt_event_handle_t event = data;

    switch (id) {
        case MQTT_EVENT_CONNECTED:
            ESP_LOGI(TAG, "✅ MQTT Conectado!");
            esp_mqtt_client_subscribe(client, "sala/" SALA_ID "/comando", 0);
            ESP_LOGI(TAG, "📡 Inscrito em: sala/" SALA_ID "/comando");
            break;

        case MQTT_EVENT_DATA: {
            char topico[64] = {0};
            char payload[32] = {0};
            strncpy(topico, event->topic, event->topic_len);
            strncpy(payload, event->data, event->data_len);
            ESP_LOGI(TAG, "📩 Comando recebido: %s → %s", topico, payload);

            if (strcmp(payload, "ON") == 0) {
                gpio_set_level(RELAY_LIGHT_PIN, 1);
                ESP_LOGI(TAG, "💡 Relé LIGADO via Telegram");
            } else if (strcmp(payload, "OFF") == 0) {
                gpio_set_level(RELAY_LIGHT_PIN, 0);
                ESP_LOGI(TAG, "🛑 Relé DESLIGADO via Telegram");
            }
            break;
        }

        case MQTT_EVENT_DISCONNECTED:
            ESP_LOGW(TAG, "MQTT desconectado.");
            break;

        default:
            break;
    }
}

static void mqtt_app_start(void) {
    esp_mqtt_client_config_t mqtt_cfg = {
        .broker.address.uri = BROKER_URL,
        .credentials.username = "iot_user",
        .credentials.authentication.password = "iot_pass123",
    };
    client = esp_mqtt_client_init(&mqtt_cfg);
    esp_mqtt_client_register_event(client, ESP_EVENT_ANY_ID, mqtt_event_handler, NULL);
    esp_mqtt_client_start(client);
    ESP_LOGI(TAG, "Conectando ao Broker MQTT em %s...", BROKER_URL);
}

// --- Device Info ---

static void publish_device_info(void) {
    if (client == NULL) return;

    char ip_str[16] = "0.0.0.0";
    if (s_netif != NULL) {
        esp_netif_ip_info_t ip_info = {0};
        if (esp_netif_get_ip_info(s_netif, &ip_info) == ESP_OK) {
            snprintf(ip_str, sizeof(ip_str), IPSTR, IP2STR(&ip_info.ip));
        }
    }

    int8_t rssi = 0;
    wifi_ap_record_t ap_info = {0};
    if (esp_wifi_sta_get_ap_info(&ap_info) == ESP_OK) {
        rssi = ap_info.rssi;
    }

    uint32_t uptime = (uint32_t)(esp_timer_get_time() / 1000000ULL);

    char payload[96];
    snprintf(payload, sizeof(payload),
        "{\"uptime\":%lu,\"rssi\":%d,\"ip\":\"%s\"}",
        (unsigned long)uptime, (int)rssi, ip_str);

    char topico[64];
    snprintf(topico, sizeof(topico), "sala/%s/info", SALA_ID);
    esp_mqtt_client_publish(client, topico, payload, 0, 0, 0);
    ESP_LOGI(TAG, "📊 Info: %s", payload);
}

// --- GPIOs ---

void iniciar_gpios(void) {
    gpio_reset_pin(RELAY_LIGHT_PIN);
    gpio_set_direction(RELAY_LIGHT_PIN, GPIO_MODE_OUTPUT);
    gpio_set_level(RELAY_LIGHT_PIN, 1);

    gpio_reset_pin(PIR_SENSOR_PIN);
    gpio_set_direction(PIR_SENSOR_PIN, GPIO_MODE_INPUT);
    gpio_set_pull_mode(PIR_SENSOR_PIN, GPIO_PULLDOWN_ONLY);

    gpio_reset_pin(LDR_SENSOR_PIN);
    gpio_set_direction(LDR_SENSOR_PIN, GPIO_MODE_INPUT);
    gpio_set_pull_mode(LDR_SENSOR_PIN, GPIO_PULLUP_ONLY);

    ESP_LOGI(TAG, "GPIOs inicializados.");
}

// --- Main ---

void app_main(void) {
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    iniciar_gpios();
    wifi_init_sta();
    mqtt_app_start();

    int ultimo_movimento = -1;
    int ultimo_ldr = -1;
    int info_ticks = 0;
#define INFO_PUBLISH_EVERY 60  // 60 x 500ms = 30s

    char topico_pir[64];
    char topico_ldr[64];
    char topico_log[64];
    snprintf(topico_pir, sizeof(topico_pir), "sala/%s/ocupacao", SALA_ID);
    snprintf(topico_ldr, sizeof(topico_ldr), "sala/%s/luminosidade", SALA_ID);
    snprintf(topico_log, sizeof(topico_log), "sala/%s/log", SALA_ID);

    while (1) {
        int movimento = gpio_get_level(PIR_SENSOR_PIN);

        if (movimento != ultimo_movimento) {
            ultimo_movimento = movimento;
            char payload[2];
            snprintf(payload, sizeof(payload), "%d", movimento);
            esp_mqtt_client_publish(client, topico_pir, payload, 0, 0, 0);

            if (movimento) {
                ESP_LOGI(TAG, "🚶 Movimento detectado!");
                esp_mqtt_client_publish(client, topico_log, "Movimento detectado", 0, 0, 0);
            } else {
                ESP_LOGI(TAG, "💤 Sem movimento.");
                esp_mqtt_client_publish(client, topico_log, "Sem movimento", 0, 0, 0);
            }
        }

        int ldr_raw = gpio_get_level(LDR_SENSOR_PIN);
        int ldr = (ldr_raw == 0) ? 1 : 0;

        if (ldr != ultimo_ldr) {
            ultimo_ldr = ldr;
            char payload_ldr[2];
            snprintf(payload_ldr, sizeof(payload_ldr), "%d", ldr);
            esp_mqtt_client_publish(client, topico_ldr, payload_ldr, 0, 0, 0);

            if (ldr) {
                ESP_LOGI(TAG, "💡 Luz acesa");
                esp_mqtt_client_publish(client, topico_log, "Luz acesa", 0, 0, 0);
            } else {
                ESP_LOGI(TAG, "🌑 Luz apagada");
                esp_mqtt_client_publish(client, topico_log, "Luz apagada", 0, 0, 0);
            }
        }

        info_ticks++;
        if (info_ticks >= INFO_PUBLISH_EVERY) {
            info_ticks = 0;
            publish_device_info();
        }

        vTaskDelay(pdMS_TO_TICKS(500));
    }
}
