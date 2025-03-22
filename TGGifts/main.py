import requests
from bs4 import BeautifulSoup
import time
import json
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()
TELEGRAM_BOT_TOKEN = '7247854140:AAEr-u2jkzj6SKOCyyr7lfydSKov1ljbYHI'
TELEGRAM_CHANNEL_IDS = -1002269413608  # через запятую, если несколько

GIFT_TYPES_FILE = "gift_types.json"
LAST_MINTED_FILE = "last_minted.json"

def load_gift_types():
    """Загружает список типов подарков из JSON-файла или создаёт файл с дефолтным списком."""
    default_gift_types = []
    if os.path.exists(GIFT_TYPES_FILE):
        try:
            with open(GIFT_TYPES_FILE, "r", encoding="utf-8") as f:
                gift_types = json.load(f)
                if not isinstance(gift_types, list):
                    gift_types = default_gift_types
        except Exception as e:
            print("Ошибка загрузки gift_types:", e)
            gift_types = default_gift_types
    else:
        gift_types = default_gift_types
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
        response = requests.get(url, allow_redirects=True)
        final_url = response.url

        if "telegram.org" in final_url and "/nft/" not in final_url:
            return False, None, None

        soup = BeautifulSoup(response.text, "html.parser")
        quantity_th = soup.find("th", string="Quantity")
        if not quantity_th:
            return True, None, None

        quantity_td = quantity_th.find_next("td")
        if not quantity_td:
            return True, None, None

        quantity_text = quantity_td.get_text(strip=True)
        quantity_text = quantity_text.replace("issued", "").strip()
        left_part, right_part = quantity_text.split("/")
        minted_str = left_part.replace("\xa0", "").replace(" ", "")
        total_str  = right_part.replace("\xa0", "").replace(" ", "")
        minted = int(minted_str)
        total  = int(total_str)
        return True, minted, total

    except requests.RequestException:
        return False, None, None
    except (ValueError, AttributeError):
        return True, None, None

def send_telegram_message(message):
    """Отправляет сообщение в указанные Telegram каналы через Bot API с обработкой ошибки 429."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_IDS:
        print("Telegram бот токен или channel id не настроены в .env")
        return

    channel_ids = [cid.strip() for cid in TELEGRAM_CHANNEL_IDS.split(",") if cid.strip()]
    for chat_id in channel_ids:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        try:
            response = requests.post(url, data=payload)
            if response.status_code != 200:
                if response.status_code == 429:
                    try:
                        resp_json = response.json()
                        retry_after = resp_json.get("parameters", {}).get("retry_after", 1)
                        print(f"Rate limit hit для канала {chat_id}. Ждем {retry_after} секунд.")
                        time.sleep(retry_after)
                        # Повторная отправка после ожидания
                        response = requests.post(url, data=payload)
                        if response.status_code != 200:
                            print(f"Ошибка отправки в канал {chat_id} после retry: {response.text}")
                    except Exception as ex:
                        print(f"Ошибка обработки 429 для канала {chat_id}: {ex}")
                else:
                    print(f"Ошибка отправки в канал {chat_id}: {response.text}")
            # Небольшая задержка между отправками сообщений для разных каналов
            time.sleep(0.5)
        except Exception as e:
            print(f"Ошибка отправки в канал {chat_id}: {e}")

# Загружаем список типов подарков из файла gift_types.json
gift_types = load_gift_types()

# Для каждого подарка используем фиксированный URL, например, https://t.me/nft/{gift}-1
gift_urls = { gift: f"https://t.me/nft/{gift}-1" for gift in gift_types }

# Загружаем ранее сохранённые значения "minted" для каждого подарка.
last_minted = load_last_minted()

# Если для какого-либо подарка значения нет, устанавливаем начальное значение равное 1.
for gift in gift_types:
    if gift not in last_minted:
        last_minted[gift] = 1

print("Запуск парсинга страниц подарков. Каждую секунду проверяем изменения значений.\n")

try:
    while True:
        for gift in gift_types:
            url = gift_urls[gift]
            exists, minted, total = parse_telegram_gift(url)
            if exists and minted is not None and last_minted[gift] != 1:
                # Формируем URL с обновленным значением minted
                current_url = url[:-1] + str(minted)
                if minted > last_minted[gift]:
                    message = (f"<b>Новый подарок {gift} обнаружен!</b>\n"
                               f"URL: {current_url}\n"
                               f"Количество подарков: {minted} из {total}")
                    print(message)
                    send_telegram_message(message)
                    last_minted[gift] = minted
                    save_last_minted(last_minted)
        time.sleep(1)
except KeyboardInterrupt:
    print("\nЗавершение работы. Выход из программы.")
