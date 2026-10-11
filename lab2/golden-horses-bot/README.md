# Golden Horses Bot 🐴

Telegram-бот для записи на прогулки на лошадях в Токсово (СПб).

## Возможности

- 🐴 Запись на прогулку: услуга, анкета, дата, время
- 📋 Просмотр своих записей
- 💰 Прайс-лист
- 📍 Как добраться
- 📝 Памятка посетителя
- 📞 Контакты
- ℹ️ О нас
- 🐴 Наши лошади из `data/horses.csv`
- 👥 Наши инструкторы из `data/instructors.csv`
- 🔍 Поиск лошадей по имени или породе
- 🔍 Поиск инструкторов по специализации

## Источники данных

Бот читает данные из файлов:

- `data/bookings.json` — записи пользователей
- `data/horses.csv` — список лошадей
- `data/instructors.csv` — список инструкторов
- `data/services.csv` — дополнительный справочник, если понадобится расширение

Если CSV-файл отсутствует или повреждён, бот покажет сообщение: `Данные временно недоступны`.

## Установка

```bash
pip install -r requirements.txt
```

## Настройка

Создайте файл `.env` рядом с `bot.py` и добавьте токен:

```env
BOT_TOKEN=your_telegram_bot_token_here
```

## Запуск

```bash
python bot.py
```

## Формат CSV

### `data/horses.csv`

Колонки:

```csv
name,breed,age,color,character,height_cm,max_weight_kg
```

### `data/instructors.csv`

Колонки:

```csv
name,specialization,experience_years,phone,languages
```

## Примечания

- Для записи на прогулку используется `ConversationHandler`
- Записи сохраняются в JSON, с полем `total_price`
- VIP-прогулки доступны только для двоих
- После подтверждения заявки бот показывает памятку отдельным сообщением
