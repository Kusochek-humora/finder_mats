# MatFinder — деплой на VPS

## 1. Установка зависимостей на сервере

```bash
sudo apt update
sudo apt install python3-pip ffmpeg -y
pip3 install -r requirements.txt
```

## 2. Настройка Telegram бота

1. Напиши @BotFather в Telegram → /newbot → получи токен
2. Узнай свой chat_id: напиши боту любое сообщение, затем открой:
   https://api.telegram.org/bot<ВАШ_ТОКЕН>/getUpdates
   → найди "id" в блоке "chat"

3. Вставь в main.py:
   TELEGRAM_TOKEN = "123456:ABC-DEF..."
   TELEGRAM_CHAT_ID = "123456789"

## 3. Запуск

```bash
# Тест
uvicorn main:app --host 0.0.0.0 --port 8000

# Постоянная работа (через screen)
screen -S matfinder
uvicorn main:app --host 0.0.0.0 --port 8000
# Ctrl+A, D — свернуть
```

## 4. Nginx (опционально, чтобы работало на 80 порту)

```nginx
server {
    listen 80;
    server_name ВАШ_IP;

    client_max_body_size 200M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_read_timeout 600;
    }
}
```

```bash
sudo nano /etc/nginx/sites-available/matfinder
# вставить конфиг выше
sudo ln -s /etc/nginx/sites-available/matfinder /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## Структура проекта

```
matfinder/
├── main.py           # FastAPI бэкенд
├── requirements.txt  # зависимости
└── templates/
    └── index.html    # фронтенд
```
