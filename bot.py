import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ChatMemberStatus
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "SIZNING_BOT_TOKENINGIZ")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://SIZNING-MANZILINGIZ.example/index.html")

CHANNELS = [
    {"chat_id": -1004456522779, "title": "Kanal", "url": "https://t.me/+h_v3VMarrg1jZDky"},
    {"chat_id": -5045021834, "title": "Guruh", "url": "https://t.me/+nr-zepe-5bZhMzU6"},
]

logging.basicConfig(level=logging.INFO)
router = Router()

verified_users: set[int] = set()


class Form(StatesGroup):
    waiting_name = State()


def subscribe_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=f"➕ {ch['title']}", url=ch["url"])]
        for ch in CHANNELS
    ]
    buttons.append(
        [InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def webapp_keyboard() -> InlineKeyboardMarkup:
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


async def is_subscribed(bot: Bot, user_id: int) -> bool:
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


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    if message.from_user.id in verified_users:
        await ask_name(message, state)
        return

    if await is_subscribed(message.bot, message.from_user.id):
        verified_users.add(message.from_user.id)
        await ask_name(message, state)
        return

    await message.answer(
        "Assalomu alaykum! 👋\n\n"
        "Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling, "
        "so'ngra <b>«✅ Obunani tekshirish»</b> tugmasini bosing:",
        reply_markup=subscribe_keyboard(),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "check_sub")
async def check_subscription(callback: CallbackQuery, state: FSMContext):
    if await is_subscribed(callback.bot, callback.from_user.id):
        verified_users.add(callback.from_user.id)
        await callback.message.edit_text("✅ Obuna tasdiqlandi, rahmat!")
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

    await state.update_data(name=name)
    await state.clear()

    await message.answer(
        f"Rahmat, <b>{name}</b>! 🎉\n\n"
        "<b>Kino Top</b> — eng yaxshi filmlar to'plamiga xush kelibsiz.\n"
        "Pastdagi tugmani bosib, ilovani oching:",
        reply_markup=webapp_keyboard(),
        parse_mode=ParseMode.HTML,
    )


async def main():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
