#!/bin/bash

# Чтение данных из server.json
SERVER_URL=$(jq -r '.server_url' server.json)  # Адрес сервера
API_KEY=$(jq -r '.api_key' server.json)        # API ключ

# Настройка GPIO
GPIO_PIN=7
gpio mode $GPIO_PIN in
linphonecsh dial 10000
# Проверяем начальное состояние GPIO
echo "Инициализация GPIO..."
while [ "$(gpio read $GPIO_PIN)" -eq 0 ]; do
    echo "Ожидание размыкания GPIO $GPIO_PIN..."
    sleep 0.1
done

# Функция для обработки нажатия
on_gpio_trigger() {
    echo "$(date): GPIO $GPIO_PIN активирован. Выполняется команда:"
    linphonecsh dial 1300
    # Чтение данных из файла incident.json и обновление поля date_time
    INCIDENT_JSON=$(cat incident.json | jq --arg date_time "$(date --iso-8601=seconds)" '.date_time = $date_time')

    # Отправка POST запроса с использованием curl
    curl -X POST "$SERVER_URL" \
        -H "Content-Type: application/json" \
        -H "x-api-key: $API_KEY" \
        -d "$INCIDENT_JSON"
    
    sleep 1  # Задержка для защиты от дребезга
}

# Основной цикл
echo "Ожидание замыкания GPIO $GPIO_PIN..."
while true; do
    # Проверяем состояние GPIO
    if [ "$(gpio read $GPIO_PIN)" -eq 0 ]; then
        on_gpio_trigger
        # Ждем, пока пин снова станет HIGH, чтобы избежать повторного срабатывания
        while [ "$(gpio read $GPIO_PIN)" -eq 0 ]; do
            sleep 0.1
        done
        echo "$(date): Ожидание следующего замыкания..."
    fi
    sleep 0.1
done
