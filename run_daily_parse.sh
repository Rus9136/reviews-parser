#!/bin/bash
# Wrapper script for daily parsing

PROJECT_DIR="/root/projects/reviews-parser"
VENV_PATH="$PROJECT_DIR/venv"
LOG_DIR="$PROJECT_DIR/logs"

# Загрузка переменных окружения
source "$PROJECT_DIR/.env"
export DATABASE_URL
export PARSER_API_KEY

# Активация виртуального окружения
source "$VENV_PATH/bin/activate"

# Переход в директорию проекта
cd "$PROJECT_DIR"

# Запуск парсинга с логированием
echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting daily parse" >> "$LOG_DIR/cron.log"
python daily_parse.py >> "$LOG_DIR/cron.log" 2>&1
EXIT_CODE=$?
echo "$(date '+%Y-%m-%d %H:%M:%S') - Daily parse finished with exit code: $EXIT_CODE" >> "$LOG_DIR/cron.log"

exit $EXIT_CODE
