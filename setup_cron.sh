#!/bin/bash
# Скрипт для настройки cron job для ежедневного парсинга отзывов

PROJECT_DIR="/root/projects/reviews-parser"
VENV_PATH="$PROJECT_DIR/venv"
PYTHON_PATH="$VENV_PATH/bin/python"
SCRIPT_PATH="$PROJECT_DIR/daily_parse.py"
LOG_DIR="$PROJECT_DIR/logs"
CRON_LOG="$LOG_DIR/cron.log"

# Создание директории для логов
mkdir -p "$LOG_DIR"

# Создание wrapper скрипта для cron
WRAPPER_SCRIPT="$PROJECT_DIR/run_daily_parse.sh"

cat > "$WRAPPER_SCRIPT" << 'EOF'
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
EOF

# Делаем wrapper скрипт исполняемым
chmod +x "$WRAPPER_SCRIPT"

# Проверяем, есть ли уже cron задание для парсинга
CRON_EXISTS=$(crontab -l 2>/dev/null | grep -c "run_daily_parse.sh")

if [ "$CRON_EXISTS" -eq 0 ]; then
    # Добавляем cron задание (запуск каждый день в 3:00 ночи)
    (crontab -l 2>/dev/null; echo "0 3 * * * $WRAPPER_SCRIPT") | crontab -
    echo "✅ Cron задание успешно добавлено"
    echo "   Парсинг будет запускаться каждый день в 3:00 ночи"
else
    echo "⚠️  Cron задание уже существует"
fi

# Вывод текущих cron заданий
echo ""
echo "📋 Текущие cron задания:"
crontab -l | grep "run_daily_parse.sh"

echo ""
echo "🔧 Полезные команды:"
echo "   - Просмотр cron заданий: crontab -l"
echo "   - Редактирование cron: crontab -e"
echo "   - Удаление cron задания: crontab -r"
echo "   - Просмотр логов: tail -f $LOG_DIR/cron.log"
echo "   - Ручной запуск: $WRAPPER_SCRIPT"
echo ""
echo "📝 Формат cron задания:"
echo "   0 3 * * * - запуск каждый день в 3:00"
echo "   */30 * * * * - запуск каждые 30 минут"
echo "   0 */6 * * * - запуск каждые 6 часов"