#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "esp_log.h"

#define PIR_SENSOR_PIN    2 // Entrada: Sensor de movimento HC-SR501
#define LIGHT_SENSOR_PIN  3 // Entrada: Sensor de luminosidade LDR
#define RELAY_LIGHT_PIN   4 // Saída: Relé de Iluminação

static const char *TAG = "SISTEMA_EDGE";

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
    iniciar_gpios();

    while (1) {
        int movimento    = gpio_get_level(PIR_SENSOR_PIN);
        int luminosidade = gpio_get_level(LIGHT_SENSOR_PIN);

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

        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}