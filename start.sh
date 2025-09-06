#!/bin/bash

# Активируем виртуальное окружение (если используется)
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Устанавливаем зависимости
pip install -r requirements.txt

# Запускаем бота
python start.py