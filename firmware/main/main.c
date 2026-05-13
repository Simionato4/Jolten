#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "esp_log.h"

#define PIR_SENSOR_PIN    4   // Entrada: Sensor de movimento HC-SR501
#define RELAY_LIGHT_PIN   18  // Saída: Relé SSR da Iluminação
#define RELAY_AC_PIN      19  // Saída: Relé SSR do Ar-Condicionado

static const char *TAG = "SISTEMA_EDGE";

void iniciar_gpios() {
    gpio_reset_pin(RELAY_LIGHT_PIN);
    gpio_set_direction(RELAY_LIGHT_PIN, GPIO_MODE_OUTPUT);
    
    gpio_reset_pin(RELAY_AC_PIN);
    gpio_set_direction(RELAY_AC_PIN, GPIO_MODE_OUTPUT);

    gpio_reset_pin(PIR_SENSOR_PIN);
    gpio_set_direction(PIR_SENSOR_PIN, GPIO_MODE_INPUT);
    gpio_set_pull_mode(PIR_SENSOR_PIN, GPIO_PULLDOWN_ONLY);

    ESP_LOGI(TAG, "GPIOs inicializados com sucesso.");
}

void app_main(void) {
    iniciar_gpios();

    while (1) {
        int movimento = gpio_get_level(PIR_SENSOR_PIN);

        if (movimento) {
            ESP_LOGI(TAG, "Movimento detectado! Ligando cargas...");
            gpio_set_level(RELAY_LIGHT_PIN, 1);
            gpio_set_level(RELAY_AC_PIN, 1);
        } else {
            ESP_LOGW(TAG, "Sala vazia...");
            // A lógica de timeout de 60 minutos será implementada a seguir [cite: 79, 87]
        }

        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}