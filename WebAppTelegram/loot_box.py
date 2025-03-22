import random
import asyncio
from aiogram import types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from werkzeug.datastructures import Range

# Список возможных наград
REWARDS = [
    "💰 100 монет",
    "⚔️ Редкий меч",
    "🛡 Щит",
    "💎 Драгоценный камень",
    "✨ Магический свиток",
    "🍀 Амулет удачи",
]

async def send_loot_box(message: types.Message):
    """Отправляет сообщение с дизайном лут-бокса и кнопкой для его открытия."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Открыть лут-бокс 🎁", callback_data="open_loot_box")]
        ]
    )
    loot_box_design = (
        "🎉 <b>Лут-бокс</b> 🎉\n"
        "Внутри скрыты ценные призы!\n"
        "Нажмите кнопку ниже, чтобы открыть его."
    )
    await message.answer(loot_box_design, reply_markup=keyboard)

async def open_loot_box(callback: CallbackQuery):
    """Обрабатывает открытие лут-бокса и отправляет награду."""
    for i in range(4):
        await callback.answer(f"Открытие лут-бокса{i}", show_alert=True)
    # Задержка для имитации анимации открытия
    await asyncio.sleep(1)
    reward = random.choice(REWARDS)
    result_text = (
        "🎊 <b>Поздравляем!</b> 🎊\n"
        f"Вы получили: {reward}\n\n"
        "Попробуйте снова, введя команду /loot."
    )
    await callback.message.edit_text(result_text)
