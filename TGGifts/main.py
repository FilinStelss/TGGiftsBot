import requests
from bs4 import BeautifulSoup
import time
import json
import os
import asyncio
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()
BOT_TOKEN = '7247854140:AAEr-u2jkzj6SKOCyyr7lfydSKov1ljbYHI'
# TELEGRAM_CHANNELS задаётся через запятую, например: @channel1,@channel2
CHANNELS = [-1002269413608]

GIFT_TYPES_FILE = "gift_types.json"
LAST_MINTED_FILE = "last_minted.json"


def load_gift_types():
    """Загружает список типов подарков или создаёт файл с дефолтным списком."""
    default_gift_types = []
    if not os.path.exists(GIFT_TYPES_FILE):
        with open(GIFT_TYPES_FILE, "w", encoding="utf-8") as f:
            json.dump(default_gift_types, f, indent=4, ensure_ascii=False)

    try:
        with open(GIFT_TYPES_FILE, "r", encoding="utf-8") as f:
            gift_types = json.load(f)
            if not isinstance(gift_types, list):
                return default_gift_types
            return [s.replace(" ", "") for s in gift_types]
    except Exception as e:
        print("Ошибка загрузки gift_types:", e)
        return default_gift_types


def load_last_minted(gift_types):
    """Загружает last_minted или создаёт новый с 1 для всех типов подарков."""
    last_minted = {gift: 1 for gift in gift_types}

    if not os.path.exists(LAST_MINTED_FILE):
        with open(LAST_MINTED_FILE, "w", encoding="utf-8") as f:
            json.dump(last_minted, f, indent=4, ensure_ascii=False)
        return last_minted

    try:
        with open(LAST_MINTED_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return last_minted

            # Добавляем недостающие подарки
            for gift in gift_types:
                if gift not in data:
                    data[gift] = 1
            return data
    except Exception as e:
        print("Ошибка загрузки last_minted:", e)
        return last_minted


def save_last_minted(data):
    """Сохраняет last_minted в JSON-файл."""
    try:
        with open(LAST_MINTED_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print("Ошибка сохранения JSON:", e)


# Загружаем данные
gift_types = load_gift_types()
last_minted = load_last_minted(gift_types)

def load_gift_types():
    """Загружает список типов подарков из JSON-файла или создаёт файл с дефолтным списком."""
    default_gift_types = []
    if os.path.exists(GIFT_TYPES_FILE):
        try:
            with open(GIFT_TYPES_FILE, "r", encoding="utf-8") as f:
                gift_types = json.load(f)
                # Если файл пуст или не является списком, используем значение по умолчанию
                if not isinstance(gift_types, list):
                    gift_types = default_gift_types
        except Exception as e:
            print("Ошибка загрузки gift_types:", e)
            gift_types = default_gift_types
    else:
        gift_types = default_gift_types
        # Создаём файл с дефолтными значениями
        try:
            with open(GIFT_TYPES_FILE, "w", encoding="utf-8") as f:
                json.dump(gift_types, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print("Ошибка создания gift_types файла:", e)
    return [s.replace(" ", "") for s in gift_types]

def load_last_minted():
    """Загружает данные из JSON-файла или возвращает пустой словарь."""
    if os.path.exists(LAST_MINTED_FILE):
        try:
            with open(LAST_MINTED_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("Ошибка загрузки JSON:", e)
    return {}

def save_last_minted(data):
    """Сохраняет данные в JSON-файл."""
    try:
        with open(LAST_MINTED_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print("Ошибка сохранения JSON:", e)

def parse_telegram_gift(url):
    """
    Парсит страницу подарка по URL и возвращает кортеж (gift_exists, minted, total):
      - gift_exists (bool): True, если страница подарка существует (нет редиректа на telegram.org).
      - minted (int или None): текущее количество выпущенных экземпляров.
      - total (int или None): максимальное количество.
    Если подарок не существует, возвращается (False, None, None).
    Если данные распарсить не удалось, возвращается (True, None, None).
    """
    try:
        response = requests.get(url, allow_redirects=True, timeout=10)
        final_url = response.url

        # Если произошёл редирект на telegram.org (без /nft/ в ссылке) – подарок отсутствует
        if "telegram.org" in final_url and "/nft/" not in final_url:
            return False, None, None

        soup = BeautifulSoup(response.text, "html.parser")
        quantity_th = soup.find("th", string="Quantity")
        if not quantity_th:
            return True, None, None

        quantity_td = quantity_th.find_next("td")
        if not quantity_td:
            return True, None, None

        # Ожидается строка вида "65 761/190 222 issued"
        quantity_text = quantity_td.get_text(strip=True)
        quantity_text = quantity_text.replace("issued", "").strip()
        left_part, right_part = quantity_text.split("/")
        # Убираем пробелы и неразрывные пробелы
        minted_str = left_part.replace("\xa0", "").replace(" ", "")
        total_str  = right_part.replace("\xa0", "").replace(" ", "")
        minted = int(minted_str)
        total  = int(total_str)
        return True, minted, total

    except requests.RequestException:
        return False, None, None
    except (ValueError, AttributeError):
        return True, None, None

async def send_telegram_message(message: str):
    """
    Асинхронно отправляет сообщение во все каналы, указанные в переменной CHANNELS.
    """
    if not CHANNELS:
        print("Телеграм-каналы не указаны в .env")
        return

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    for channel in CHANNELS:
        try:
            await bot.send_message(channel, message)
        except Exception as e:
            print(f"Ошибка при отправке сообщения в {channel}: {e}")
    await bot.session.close()

# Загружаем список типов подарков из файла gift_types.json
gift_types = load_gift_types()

# Для каждого подарка будем использовать фиксированный URL, например, https://t.me/nft/{gift}-1
gift_urls = { gift: f"https://t.me/nft/{gift}-1" for gift in gift_types }

# Загружаем ранее сохранённые значения "minted" для каждого подарка.
last_minted = load_last_minted()

# Если для какого-либо подарка значения нет, устанавливаем начальное значение равное 1.
for gift in gift_types:
    if gift not in last_minted:
        last_minted[gift] = 1

print("Запуск парсинга страниц подарков. Каждую секунду проверяем изменения значений.\n")

while True:
    for gift in gift_types:
        url = gift_urls[gift]
        exists, minted, total = parse_telegram_gift(url)
        # Если страница существует и удалось получить значение "minted"
        if exists and minted is not None and last_minted[gift] != 1:
            # Если новое значение больше предыдущего — отправляем уведомление
            updated_url = url[:-1] + str(minted)
            if minted > last_minted[gift]:
                message = (
                    f"<b>Новый подарок {gift} обнаружен!</b>\n"
                    f"URL: {updated_url}\n"
                    f"Количество: {last_minted[gift]} из {total}"
                )
                print(message)
                last_minted[gift] = minted
                save_last_minted(last_minted)
                # Отправляем сообщение в телеграм-каналы
                asyncio.run(send_telegram_message(message))
    time.sleep(0.01)
