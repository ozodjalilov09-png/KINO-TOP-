import asyncio
import json
import logging
import os

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ChatMemberStatus
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
)

# --- Sozlamalar ---------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "SIZNING_BOT_TOKENINGIZ")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://SIZNING-MANZILINGIZ.example/index.html")

# Admin foydalanuvchi ID'lari (vergul bilan ajratilgan), masalan: "123456789,987654321"
# O'z Telegram ID'ingizni bilish uchun @userinfobot'ga /start yozing.
ADMIN_IDS = {
    int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()
}

CHANNELS = [
    {"chat_id": -1004456522779, "title": "Kanal", "url": "https://t.me/+h_v3VMarrg1jZDky"},
    {"chat_id": -1004317457717, "title": "Guruh", "url": "https://t.me/+nr-zepe-5bZhMzU6"},
]

DATA_FILE = "users_data.json"

logging.basicConfig(level=logging.INFO)
router = Router()


# --- Ma'lumotlarni saqlash (fayl orqali, qayta ishga tushirilganda yo'qolmasin) ---

def load_users() -> dict:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.warning("users_data.json o'qilmadi: %s", e)
    return {}


def save_users(data: dict):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.warning("users_data.json yozilmadi: %s", e)


# users_db: { "user_id": {"name": str, "username": str} }
users_db: dict = load_users()


class Form(StatesGroup):
    waiting_name = State()


# --- Yordamchi funksiyalar ------------------------------------------------

def subscribe_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=f"➕ {ch['title']}", url=ch["url"])]
        for ch in CHANNELS
    ]
    buttons.append(
        [InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def webapp_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎬 Kino Top’ni ochish",
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            ]
        ]
    )


def webapp_reply_keyboard() -> ReplyKeyboardMarkup:
    """Har doim pastda turadigan doimiy tugma — qayta /start yozmasdan ochish mumkin."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎬 Kino Top’ni ochish", web_app=WebAppInfo(url=WEBAPP_URL))]
        ],
        resize_keyboard=True,
    )


async def is_subscribed(bot: Bot, user_id: int) -> bool:
    """Foydalanuvchi barcha kanallarga obuna bo'lganini tekshiradi."""
    allowed_statuses = {
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.CREATOR,
    }
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=ch["chat_id"], user_id=user_id)
            if member.status not in allowed_statuses:
                return False
        except Exception as e:
            logging.warning("Obunani tekshirishda xatolik (%s): %s", ch["chat_id"], e)
            return False
    return True


async def ask_name(message: Message, state: FSMContext):
    await state.set_state(Form.waiting_name)
    await message.answer("Zo'r! Endi, iltimos, ismingizni yozing:")


async def show_main_menu(message: Message, name: str):
    await message.answer(
        f"Xush kelibsiz, <b>{name}</b>! 🎉\n\n"
        "<b>Kino Top</b> — eng yaxshi filmlar to'plamiga xush kelibsiz.\n"
        "Pastdagi tugmani bosib, ilovani oching:",
        reply_markup=webapp_inline_keyboard(),
        parse_mode=ParseMode.HTML,
    )
    # Doimiy pastki tugmani ham yuboramiz (birinchi marta)
    await message.answer(
        "Istalgan vaqtda pastdagi tugma orqali ham ochishingiz mumkin 👇",
        reply_markup=webapp_reply_keyboard(),
    )


# --- Handlerlar -----------------------------------------------------------

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user_id = str(message.from_user.id)

    if not await is_subscribed(message.bot, message.from_user.id):
        await message.answer(
            "Assalomu alaykum! 👋\n\n"
            "Botdan foydalanish uchun quyidagilarga obuna bo'ling, "
            "so'ngra <b>«✅ Obunani tekshirish»</b> tugmasini bosing:",
            reply_markup=subscribe_keyboard(),
            parse_mode=ParseMode.HTML,
        )
        return

    # Obuna bor. Ism avval so'ralganmi tekshiramiz.
    if user_id in users_db and users_db[user_id].get("name"):
        await show_main_menu(message, users_db[user_id]["name"])
    else:
        await ask_name(message, state)


@router.callback_query(F.data == "check_sub")
async def check_subscription(callback: CallbackQuery, state: FSMContext):
    user_id = str(callback.from_user.id)

    if await is_subscribed(callback.bot, callback.from_user.id):
        await callback.message.edit_text("✅ Obuna tasdiqlandi, rahmat!")
        if user_id in users_db and users_db[user_id].get("name"):
            await show_main_menu(callback.message, users_db[user_id]["name"])
        else:
            await ask_name(callback.message, state)
    else:
        await callback.answer(
            "❌ Siz hali barcha kanallarga obuna bo'lmadingiz. "
            "Obuna bo'lib, qayta urinib ko'ring.",
            show_alert=True,
        )
    await callback.answer()


@router.message(StateFilter(Form.waiting_name))
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip() if message.text else ""
    if not name:
        await message.answer("Iltimos, ismingizni matn ko'rinishida yuboring:")
        return

    user_id = str(message.from_user.id)
    users_db[user_id] = {
        "name": name,
        "username": message.from_user.username or "",
    }
    save_users(users_db)
    await state.clear()

    await show_main_menu(message, name)


@router.message(Command("ism"))
async def change_name(message: Message, state: FSMContext):
    """Foydalanuvchi ismini qayta o'zgartirmoqchi bo'lsa shu buyruqni ishlatadi."""
    await ask_name(message, state)


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer(f"📊 Ro'yxatdan o'tganlar soni: <b>{len(users_db)}</b>", parse_mode=ParseMode.HTML)


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    """Foydalanish: xabarni shu buyruqqa javob (reply) qilib /broadcast deb yozing."""
    if message.from_user.id not in ADMIN_IDS:
        return
    if not message.reply_to_message:
        await message.answer("Xabarni forward/javob qilib, unga reply qilgan holda /broadcast deb yozing.")
        return

    sent, failed = 0, 0
    for uid in list(users_db.keys()):
        try:
            await message.reply_to_message.copy_to(chat_id=int(uid))
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)  # Telegram limitiga tegib qolmaslik uchun

    await message.answer(f"✅ Yuborildi: {sent} ta\n❌ Xato: {failed} ta")


async def main():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
