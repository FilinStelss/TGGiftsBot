import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.client.bot import DefaultBotProperties

from config import TELEGRAM_TOKEN
from loot_box import send_loot_box, open_loot_box

# Инициализация бота с указанием режима парсинга через default
bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я бот для открытия лут-боксов. Используй команду /loot для получения лут-бокса."
    )

@dp.message(Command("loot"))
async def cmd_loot(message: types.Message):
    await send_loot_box(message)

@dp.callback_query(lambda c: c.data == "open_loot_box")
async def callback_loot_box(callback: types.CallbackQuery):
    await open_loot_box(callback)

async def main():
    await dp.start_polling(bot)
