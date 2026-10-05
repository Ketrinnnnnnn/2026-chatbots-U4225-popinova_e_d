print(">>> ФАЙЛ ЗАГРУЖЕН", flush=True)

import os
import json
import logging
import uuid
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List

print(">>> СТАНДАРТНЫЕ МОДУЛИ ИМПОРТИРОВАНЫ", flush=True)

from dotenv import load_dotenv
print(">>> dotenv импортирован", flush=True)

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
print(">>> telegram импортирован", flush=True)

from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
print(">>> telegram.ext импортирован", flush=True)

# =========================
# Настройка и логирование
# =========================

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
print(f">>> ТОКЕН: {'получен' if TOKEN else 'НЕТ'}", flush=True)

if not TOKEN:
    raise RuntimeError("Не найден BOT_TOKEN в .env")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
BOOKINGS_FILE = DATA_DIR / "bookings.json"

# =========================
# Состояния ConversationHandler
# =========================

(
    SERVICE,
    PEOPLE_COUNT,
    PERSON_GENDER,
    PERSON_AGE,
    PERSON_HEIGHT,
    PERSON_WEIGHT,
    PERSON_EXPERIENCE,
    PERSON_EXPERIENCE_TEXT,
    DATE,
    DATE_CUSTOM,
    TIME,
    NAME,
    PHONE,
    CONFIRM,
) = range(14)

# =========================
# Услуги и цены
# =========================

SERVICES = {
    "exp_15": {"name": "Экспресс 15 минут", "price": 1500, "mode": "per_person"},
    "exp_30": {"name": "Экспресс 30 минут", "price": 2000, "mode": "per_person"},
    "walk_1h": {"name": "1 час по лесу", "price": 3000, "mode": "per_person"},
    "walk_1_5h": {"name": "До 1,5 часов на озеро", "price": 4000, "mode": "per_person"},
    "walk_2h": {"name": "До 2 часов к зубрам", "price": 5000, "mode": "per_person"},
    "vip_1h": {"name": "VIP 1 час по лесу", "price": 10000, "mode": "fixed_pair"},
    "vip_1_5h": {"name": "VIP 1,5 часа на озеро", "price": 12000, "mode": "fixed_pair"},
}

TIME_SLOTS = ["10:00", "12:00", "14:00", "16:00", "18:00"]

# =========================
# Хранение данных
# =========================

def ensure_data_file() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not BOOKINGS_FILE.exists():
        with open(BOOKINGS_FILE, "w", encoding="utf-8") as f:
            json.dump({"bookings": []}, f, ensure_ascii=False, indent=2)


def load_bookings() -> Dict[str, Any]:
    ensure_data_file()
    try:
        with open(BOOKINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "bookings" not in data or not isinstance(data["bookings"], list):
            return {"bookings": []}
        return data
    except (json.JSONDecodeError, OSError):
        return {"bookings": []}


def save_bookings(data: Dict[str, Any]) -> None:
    ensure_data_file()
    with open(BOOKINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_booking(booking: Dict[str, Any]) -> None:
    data = load_bookings()
    data["bookings"].append(booking)
    save_bookings(data)


def get_user_bookings(user_id: int) -> List[Dict[str, Any]]:
    data = load_bookings()
    return [b for b in data["bookings"] if b.get("user_id") == user_id]


# =========================
# Расчёт цены
# =========================

def calculate_total_price(service_key: str, people_count: int) -> int:
    service = SERVICES.get(service_key)
    if not service:
        return 0
    if service["mode"] == "fixed_pair":
        return int(service["price"])
    return int(service["price"]) * int(people_count)


def is_vip(service_key: str) -> bool:
    return SERVICES.get(service_key, {}).get("mode") == "fixed_pair"


# =========================
# Клавиатуры
# =========================

def main_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🐴 Записаться на прогулку", callback_data="menu_book")],
        [InlineKeyboardButton("📋 Мои записи", callback_data="menu_my")],
        [InlineKeyboardButton("💰 Цены", callback_data="menu_prices")],
        [InlineKeyboardButton("📍 Как добраться", callback_data="menu_map")],
        [InlineKeyboardButton("📝 Памятка посетителя", callback_data="menu_note")],
        [InlineKeyboardButton("📞 Связаться с нами", callback_data="menu_contact")],
        [InlineKeyboardButton("ℹ️ О нас", callback_data="menu_about")],
    ]
    return InlineKeyboardMarkup(keyboard)


def service_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("Экспресс 15 минут — 1500 ₽", callback_data="srv_exp_15")],
        [InlineKeyboardButton("Экспресс 30 минут — 2000 ₽", callback_data="srv_exp_30")],
        [InlineKeyboardButton("1 час по лесу — 3000 ₽", callback_data="srv_walk_1h")],
        [InlineKeyboardButton("До 1,5 часов на озеро — 4000 ₽", callback_data="srv_walk_1_5h")],
        [InlineKeyboardButton("До 2 часов к зубрам — 5000 ₽", callback_data="srv_walk_2h")],
        [InlineKeyboardButton("VIP 1 час по лесу — 10000 ₽ (на двоих)", callback_data="srv_vip_1h")],
        [InlineKeyboardButton("VIP 1,5 часа на озеро — 12000 ₽ (на двоих)", callback_data="srv_vip_1_5h")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def gender_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("М", callback_data="gender_M"),
            InlineKeyboardButton("Ж", callback_data="gender_W"),
        ]
    ])


def experience_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Нет опыта", callback_data="exp_no"),
            InlineKeyboardButton("Есть опыт", callback_data="exp_yes"),
        ]
    ])


def date_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📅 Ввести дату вручную", callback_data="date_manual")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def time_menu() -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton(t, callback_data=f"time_{t}")] for t in TIME_SLOTS]
    return InlineKeyboardMarkup(keyboard)


def confirm_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_yes")],
        [InlineKeyboardButton("❌ Отменить", callback_data="confirm_no")],
    ])


# =========================
# Тексты
# =========================

def status_text(status: str) -> str:
    return {
        "pending": "⏳ Ожидает",
        "confirmed": "✅ Подтверждена",
        "cancelled": "❌ Отменена",
    }.get(status, status)


def service_description_text() -> str:
    return (
        "Выберите услугу для записи:\n\n"
        "ЭКСПРЕСС-КАТАНИЕ (за человека):\n"
        "• Экспресс 15 минут — 1500 ₽\n"
        "• Экспресс 30 минут — 2000 ₽\n\n"
        "КОННЫЕ ПРОГУЛКИ (за 1 человека):\n"
        "• 1 час по лесу — 3000 ₽\n"
        "• До 1,5 часов на озеро — 4000 ₽\n"
        "• До 2 часов к зубрам — 5000 ₽\n\n"
        "VIP-ПРОГУЛКИ (ТОЛЬКО НА ДВОИХ):\n"
        "• VIP 1 час по лесу — 10000 ₽\n"
        "• VIP 1,5 часа на озеро — 12000 ₽"
    )


def prices_text() -> str:
    return (
        "💰 *Цены Golden Horses*\n\n"
        "ЭКСПРЕСС-КАТАНИЕ (за человека):\n"
        "• Экспресс 15 минут — 1500 ₽\n"
        "• Экспресс 30 минут — 2000 ₽\n\n"
        "КОННЫЕ ПРОГУЛКИ (за 1 человека):\n"
        "• 1 час по лесу — 3000 ₽\n"
        "• До 1,5 часов на озеро — 4000 ₽\n"
        "• До 2 часов к зубрам — 5000 ₽\n\n"
        "VIP-ПРОГУЛКИ (ТОЛЬКО НА ДВОИХ):\n"
        "• VIP 1 час по лесу — 10000 ₽\n"
        "• VIP 1,5 часа на озеро — 12000 ₽"
    )


def how_to_get_text() -> str:
    return (
        "📍 *Как добраться*\n\n"
        "Токсовское шоссе, ЦАО «Изумрудное озеро»\n"
        "По указателю: *КОННЫЕ ПРОГУЛКИ*\n\n"
        "ВК: https://vk.com/ozeroizumrudnoe\n"
        "Приехать за 15–20 минут."
    )


def note_text() -> str:
    return (
        "📝 *Памятка посетителя*\n\n"
        "• Приехать за 15–20 минут\n"
        "• Взять паспорт\n"
        "• Одежда: ноги закрыты до колена, обувь закрывает щиколотку, без каблуков\n"
        "• Без высоких причёсок\n"
        "• Угощение: мытая морковь, яблоки, сушки\n"
        "• Ограничения: вес до 105 кг (при 95+ кг рост от 175 см), возраст 5–55 лет\n"
        "• Оплата: наличные или QR\n"
        "• Отмена за сутки\n"
        "• При опоздании время сокращается"
    )


def contact_text() -> str:
    return (
        "📞 *Связаться с нами*\n\n"
        "Телефон: +7 911 100-9-100\n"
        "Сайт: мы-миниферма.рф\n"
        "ВК: https://vk.com/ozeroizumrudnoe"
    )


def about_text() -> str:
    return (
        "ℹ️ *О нас*\n\n"
        "Golden Horses — конный клуб в Токсово на территории базы «Изумрудное озеро».\n"
        "Опытные инструкторы, спокойные лошади, маршруты: лес, озеро, зубры.\n"
        "Все прогулки в шаговом формате.\n\n"
        "Кошечки Тумба, Кошка-мать и пёс Гошенька 🐾"
    )


def booking_summary(booking: Dict[str, Any]) -> str:
    people_lines = []
    for i, p in enumerate(booking.get("people", []), start=1):
        exp = p.get("experience", "—")
        if p.get("experience_text"):
            exp = f"{exp} ({p['experience_text']})"
        people_lines.append(
            f"{i}. Пол: {p.get('gender', '—')}, "
            f"возраст: {p.get('age', '—')}, "
            f"рост: {p.get('height', '—')} см, "
            f"вес: {p.get('weight', '—')} кг, "
            f"опыт: {exp}"
        )

    return (
        "Проверьте данные заявки:\n\n"
        f"Услуга: {booking.get('service', '—')}\n"
        f"Итоговая стоимость: {booking.get('total_price', '—')} ₽\n"
        f"Дата: {booking.get('date', '—')}\n"
        f"Время: {booking.get('time', '—')}\n"
        f"Имя: {booking.get('name', '—')}\n"
        f"Телефон: {booking.get('phone', '—')}\n\n"
        f"Участники:\n" + ("\n".join(people_lines) if people_lines else "—")
    )


# =========================
# Команды и меню
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(">>> ПОЛУЧЕНА КОМАНДА /start", flush=True)
    text = (
        "🐴 Добро пожаловать в *Golden Horses*!\n\n"
        "Запись на прогулки на лошадях в Токсово, Санкт-Петербург.\n"
        "Выберите нужный раздел в меню ниже."
    )
    await update.message.reply_text(text, reply_markup=main_menu(), parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "ℹ️ Доступные команды:\n"
        "/start — главное меню\n"
        "/help — помощь\n"
        "/cancel — отменить текущую запись",
        reply_markup=main_menu(),
    )


async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    print(f">>> МЕНЮ: {data}", flush=True)

    if data == "menu_my":
        bookings = get_user_bookings(query.from_user.id)
        if not bookings:
            await query.message.reply_text("📋 У вас пока нет записей.")
            return
        lines = ["📋 *Мои записи*:\n"]
        for b in sorted(bookings, key=lambda x: x.get("created_at", ""), reverse=True):
            lines.append(
                f"• `{b.get('id', '')[:8]}` — {b.get('service', '—')} — "
                f"{b.get('date', '—')} {b.get('time', '—')} — "
                f"{b.get('total_price', '—')} ₽ — "
                f"{status_text(b.get('status', ''))}"
            )
        await query.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    if data == "menu_prices":
        await query.message.reply_text(prices_text(), parse_mode="Markdown")
        return

    if data == "menu_map":
        await query.message.reply_text(
            how_to_get_text(), parse_mode="Markdown", disable_web_page_preview=True
        )
        return

    if data == "menu_note":
        await query.message.reply_text(note_text(), parse_mode="Markdown")
        return

    if data == "menu_contact":
        await query.message.reply_text(
            contact_text(), parse_mode="Markdown", disable_web_page_preview=True
        )
        return

    if data == "menu_about":
        await query.message.reply_text(about_text(), parse_mode="Markdown")
        return

    if data == "back_menu":
        await query.message.reply_text("Главное меню:", reply_markup=main_menu())


# =========================
# Запись
# =========================

async def booking_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    context.user_data.clear()
    context.user_data["booking"] = {
        "user_id": query.from_user.id,
        "username": f"@{query.from_user.username}" if query.from_user.username else "",
        "people": [],
    }

    await query.message.reply_text(
        service_description_text(),
        reply_markup=service_menu(),
    )
    return SERVICE


async def service_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    booking = context.user_data.setdefault("booking", {})

    mapping = {
        "srv_exp_15": "exp_15",
        "srv_exp_30": "exp_30",
        "srv_walk_1h": "walk_1h",
        "srv_walk_1_5h": "walk_1_5h",
        "srv_walk_2h": "walk_2h",
        "srv_vip_1h": "vip_1h",
        "srv_vip_1_5h": "vip_1_5h",
    }

    service_key = mapping.get(query.data)
    if not service_key:
        await query.message.reply_text("Не удалось выбрать услугу.")
        return SERVICE

    booking["service_key"] = service_key
    booking["service"] = SERVICES[service_key]["name"]
    booking["price"] = SERVICES[service_key]["price"]
    booking["people"] = []
    booking["current_person"] = 0

    if is_vip(service_key):
        booking["people_count"] = 2
        await query.message.reply_text(
            f"✅ VIP-прогулка «{booking['service']}» — {booking['price']} ₽ за двоих.\n\n"
            "Заполните данные для первого участника.\n\n"
            "Укажите пол участника №1:",
            reply_markup=gender_menu(),
        )
        return PERSON_GENDER

    await query.message.reply_text(
        f"✅ Выбрано: «{booking['service']}» — {booking['price']} ₽ за человека.\n\n"
        "Сколько человек будет записано? (1-5)"
    )
    return PEOPLE_COUNT


async def people_count_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("Введите число от 1 до 5.")
        return PEOPLE_COUNT

    count = int(text)
    if not (1 <= count <= 5):
        await update.message.reply_text("Количество человек должно быть от 1 до 5.")
        return PEOPLE_COUNT

    booking = context.user_data.setdefault("booking", {})
    booking["people_count"] = count
    booking["current_person"] = 0
    booking["people"] = []

    await update.message.reply_text("Укажите пол участника №1:", reply_markup=gender_menu())
    return PERSON_GENDER


async def gender_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    booking = context.user_data.setdefault("booking", {})
    current = booking.get("current_person", 0)

    if query.data not in ("gender_M", "gender_W"):
        await query.message.reply_text("Выберите пол кнопкой.")
        return PERSON_GENDER

    booking.setdefault("people", [])
    while len(booking["people"]) <= current:
        booking["people"].append({})

    booking["people"][current]["gender"] = "М" if query.data == "gender_M" else "Ж"

    await query.message.reply_text("Возраст участника (5-55 лет):")
    return PERSON_AGE


async def age_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("Введите число от 5 до 55.")
        return PERSON_AGE

    age = int(text)
    if not (5 <= age <= 55):
        await update.message.reply_text("Возраст должен быть от 5 до 55 лет.")
        return PERSON_AGE

    booking = context.user_data.setdefault("booking", {})
    current = booking.get("current_person", 0)
    booking["people"][current]["age"] = age

    await update.message.reply_text("Рост участника (см):")
    return PERSON_HEIGHT


async def height_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    try:
        height = int(text)
    except ValueError:
        await update.message.reply_text("Введите рост числом в сантиметрах.")
        return PERSON_HEIGHT

    if height <= 0:
        await update.message.reply_text("Рост должен быть больше 0. Введите рост в сантиметрах:")
        return PERSON_HEIGHT

    if height > 250:
        await update.message.reply_text("Введите реалистичный рост в сантиметрах.")
        return PERSON_HEIGHT

    booking = context.user_data.setdefault("booking", {})
    current = booking.get("current_person", 0)
    booking["people"][current]["height"] = height

    await update.message.reply_text("Вес участника (кг):")
    return PERSON_WEIGHT


async def weight_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    try:
        weight = int(text)
    except ValueError:
        await update.message.reply_text("Введите вес числом в килограммах.")
        return PERSON_WEIGHT

    if weight <= 0:
        await update.message.reply_text("Вес должен быть больше 0. Введите вес в килограммах:")
        return PERSON_WEIGHT

    if weight > 200:
        await update.message.reply_text("Введите реалистичный вес в килограммах.")
        return PERSON_WEIGHT

    booking = context.user_data.setdefault("booking", {})
    current = booking.get("current_person", 0)
    booking["people"][current]["weight"] = weight

    await update.message.reply_text("Есть ли опыт верховой езды?", reply_markup=experience_menu())
    return PERSON_EXPERIENCE


async def experience_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    booking = context.user_data.setdefault("booking", {})
    current = booking.get("current_person", 0)

    if query.data == "exp_no":
        booking["people"][current]["experience"] = "Нет опыта"
        await next_person_or_date(query.message, context)
        return DATE

    if query.data == "exp_yes":
        booking["people"][current]["experience"] = "Есть опыт"
        await query.message.reply_text("Кратко опишите ваш опыт верховой езды:")
        return PERSON_EXPERIENCE_TEXT

    await query.message.reply_text("Выберите вариант кнопкой.")
    return PERSON_EXPERIENCE


async def experience_text_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("Опишите ваш опыт текстом.")
        return PERSON_EXPERIENCE_TEXT

    booking = context.user_data.setdefault("booking", {})
    current = booking.get("current_person", 0)
    booking["people"][current]["experience_text"] = text

    await next_person_or_date(update.message, context)
    return DATE


async def next_person_or_date(message, context: ContextTypes.DEFAULT_TYPE) -> None:
    booking = context.user_data.setdefault("booking", {})
    current = booking.get("current_person", 0)
    count = booking.get("people_count", 1)

    if current + 1 < count:
        booking["current_person"] = current + 1
        await message.reply_text(
            f"Укажите пол участника №{current + 2}:",
            reply_markup=gender_menu(),
        )
    else:
        await message.reply_text("Выберите дату прогулки:", reply_markup=date_menu())


async def date_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "date_manual":
        await query.message.reply_text("Введите дату в формате ДД.ММ.ГГГГ:")
        return DATE_CUSTOM

    await query.message.reply_text("Выберите дату кнопкой.")
    return DATE


async def custom_date_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    try:
        dt = datetime.strptime(text, "%d.%m.%Y").date()
    except ValueError:
        await update.message.reply_text("Неверный формат. Введите дату как ДД.ММ.ГГГГ.")
        return DATE_CUSTOM

    if dt < date.today():
        await update.message.reply_text("Дата не может быть в прошлом.")
        return DATE_CUSTOM

    booking = context.user_data.setdefault("booking", {})
    booking["date"] = dt.strftime("%d.%m.%Y")

    await update.message.reply_text("Выберите время:", reply_markup=time_menu())
    return TIME


async def time_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if not query.data.startswith("time_"):
        await query.message.reply_text("Выберите время кнопкой.")
        return TIME

    booking = context.user_data.setdefault("booking", {})
    booking["time"] = query.data.replace("time_", "")

    await query.message.reply_text("Введите имя и фамилию:")
    return NAME


async def name_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if len(text) < 2:
        await update.message.reply_text("Введите имя и фамилию.")
        return NAME

    booking = context.user_data.setdefault("booking", {})
    booking["name"] = text

    await update.message.reply_text("Введите телефон в формате +79990000000:")
    return PHONE


async def phone_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if len(text) < 10:
        await update.message.reply_text("Введите корректный номер телефона.")
        return PHONE

    booking = context.user_data.setdefault("booking", {})
    booking["phone"] = text

    service_key = booking.get("service_key")
    people_count = len(booking.get("people", [])) or booking.get("people_count", 1)
    booking["total_price"] = calculate_total_price(service_key, people_count)

    preview = {
        "service": booking.get("service"),
        "total_price": booking.get("total_price"),
        "date": booking.get("date"),
        "time": booking.get("time"),
        "name": booking.get("name"),
        "phone": booking.get("phone"),
        "people": booking.get("people", []),
    }
    await update.message.reply_text(
        booking_summary(preview),
        reply_markup=confirm_menu(),
    )
    return CONFIRM


async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    booking = context.user_data.get("booking", {})

    if query.data == "confirm_no":
        context.user_data.clear()
        await query.message.reply_text("Заявка отменена.", reply_markup=main_menu())
        return ConversationHandler.END

    if query.data != "confirm_yes":
        await query.message.reply_text("Выберите действие кнопкой.")
        return CONFIRM

    final_booking = {
        "id": str(uuid.uuid4()),
        "user_id": query.from_user.id,
        "username": f"@{query.from_user.username}" if query.from_user.username else "",
        "service": booking.get("service", ""),
        "price": booking.get("price", 0),
        "total_price": booking.get("total_price", 0),
        "date": booking.get("date", ""),
        "time": booking.get("time", ""),
        "name": booking.get("name", ""),
        "phone": booking.get("phone", ""),
        "people": booking.get("people", []),
        "status": "pending",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

    add_booking(final_booking)
    context.user_data.clear()

    await query.message.reply_text(note_text(), parse_mode="Markdown")
    await query.message.reply_text(
        "✅ Ваша заявка отправлена! Инструктор проверит данные и подтвердит запись.",
        reply_markup=main_menu(),
    )
    return ConversationHandler.END


async def booking_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Запись отменена.", reply_markup=main_menu())
    return ConversationHandler.END


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Ошибка в боте: %s", context.error)


# =========================
# Сборка приложения
# =========================

def build_app() -> Application:
    print(">>> build_app: начало", flush=True)
    app = ApplicationBuilder().token(TOKEN).build()
    print(">>> build_app: app создан", flush=True)

    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(booking_start, pattern=r"^menu_book$"),
        ],
        states={
            SERVICE: [
                CallbackQueryHandler(service_chosen, pattern=r"^srv_"),
                CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern=r"^back_menu$"),
            ],
            PEOPLE_COUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, people_count_received),
            ],
            PERSON_GENDER: [
                CallbackQueryHandler(gender_chosen, pattern=r"^gender_"),
            ],
            PERSON_AGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, age_received),
            ],
            PERSON_HEIGHT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, height_received),
            ],
            PERSON_WEIGHT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, weight_received),
            ],
            PERSON_EXPERIENCE: [
                CallbackQueryHandler(experience_chosen, pattern=r"^exp_(no|yes)$"),
            ],
            PERSON_EXPERIENCE_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, experience_text_received),
            ],
            DATE: [
                CallbackQueryHandler(date_chosen, pattern=r"^date_"),
            ],
            DATE_CUSTOM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, custom_date_received),
            ],
            TIME: [
                CallbackQueryHandler(time_chosen, pattern=r"^time_"),
            ],
            NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, name_received),
            ],
            PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, phone_received),
            ],
            CONFIRM: [
                CallbackQueryHandler(confirm_booking, pattern=r"^confirm_(yes|no)$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", booking_cancel),
        ],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(menu_router, pattern=r"^menu_|^back_menu$"))
    app.add_error_handler(error_handler)

    print(">>> build_app: хендлеры добавлены", flush=True)
    return app



async def run_bot() -> None:
    print(">>> run_bot() НАЧАЛАСЬ", flush=True)
    ensure_data_file()
    print(">>> data файл создан", flush=True)
    app = build_app()
    print(">>> app построен", flush=True)
    await app.initialize()
    print(">>> app инициализирован", flush=True)
    await app.start()
    print(">>> app запущен", flush=True)
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    print(">>> polling запущен, бот работает!", flush=True)
    # Бесконечное ожидание, пока бот работает
    import asyncio
    await asyncio.Event().wait()


def main() -> None:
    print(">>> main() НАЧАЛАСЬ", flush=True)
    import asyncio
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print(">>> Бот остановлен вручную", flush=True)


if __name__ == "__main__":
    print(">>> ЗАПУСК MAIN", flush=True)
    main()
