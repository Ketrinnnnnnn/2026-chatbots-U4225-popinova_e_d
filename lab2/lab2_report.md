University: [ITMO University](https://itmo.ru/ru/)
Faculty: [FICT](https://fict.itmo.ru)
Course: [Vibe Coding: AI-боты для бизнеса](https://github.com/itmo-ict-faculty/vibe-coding-for-business)
Year: 2025/2026
Group: U4225
Author: Попинова Екатерина Дмитриевна
Lab: Lab2
Date of create: 11.10.2026
Date of finished: ХХ.10.2026

---

# Лабораторная работа №2
## "Подключение бота к данным"

---

## 1. Описание интеграции

### Источник данных

**CSV-файлы** с информацией о клубе «Golden Horses»:
- `data/horses.csv` — лошади
- `data/instructors.csv` — инструкторы

### Почему выбрали CSV

1. **Простота** — не требует API-ключей и внешних сервисов.
2. **Гибкость** — легко редактировать в Excel/Notepad.
3. **Релевантность** — данные о лошадях и инструкторах — реальная информация клуба.
4. **Расширяемость** — можно добавлять поля без переписывания кода.

### Структура данных

**horses.csv:**
```csv
name,breed,age,color,character,height_cm,max_weight_kg
Абрикос,Орловский рысак,8,гнедой,Спокойный и добрый,165,90
Буян,Владимирский тяжеловоз,12,вороновой,Сильный и надёжный,175,105
...

## 2. Промпт для LLM

Итерации
Итерация 1. Добавили кнопки «🐎 Наши лошади» и «👥 Наши инструкторы».

Итерация 2. Добавили поиск по имени/породе.

Итерация 3. Добавили проверку веса всадника при записи.

Итерация 4. Добавили обработку ошибок (файл не найден).

Финальный промпт
Полный текст — в файле prompt.md.

## 3. Реализация
Как работает интеграция
Пользователь нажимает «🐎 Наши лошади» → бот читает data/horses.csv.

Парсит данные через библиотеку csv.

Форматирует — имя, порода, возраст, окрас.

Отправляет список пользователю.

При записи:

После ввода веса бот проверяет, есть ли лошадь с max_weight_kg >= weight.

Если нет — предупреждает.

## Ключевые фрагменты кода
python
import csv

def load_horses():
    """Загружает список лошадей из data/horses.csv"""
    try:
        with open("data/horses.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return [row for row in reader if row.get("name")]
    except (FileNotFoundError, OSError):
        return []

def find_horse_for_weight(weight):
    """Возвращает лошадей, подходящих по весу"""
    horses = load_horses()
    result = []
    for h in horses:
        try:
            if int(h.get("max_weight_kg", 0)) >= weight:
                result.append(h)
        except ValueError:
            continue
    return result
Используемые библиотеки
Библиотека	Назначение
csv	Чтение CSV (стандартная)
python-telegram-bot	Telegram-бот
python-dotenv	Загрузка токена
