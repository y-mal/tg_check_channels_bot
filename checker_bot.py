import asyncio, os, logging, time, hashlib
from telethon import TelegramClient, events
from dotenv import load_dotenv
import sys

# 🔧 Поддержка русских символов в логах
sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(
    filename='bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8'
)

load_dotenv()
api_id = os.getenv("api_id")
api_hash = os.getenv("api_hash")
phone = os.getenv("phone")

# Список ключевых слов
raw_keywords = []
keywords = [kw.lower() for kw in raw_keywords]

# Исключения
raw_exclude_keywords = []
exclude_keywords = [kw.lower() for kw in raw_exclude_keywords]

# Каналы для мониторинга
channels = []

target_group = int()  # Группа для пересылки

client = TelegramClient('monitor_session', api_id, api_hash)

# Хранилище последних сообщений (хеш -> timestamp)
recent_messages = {}
DUPLICATE_TIMEOUT = 15 * 60  # 15 минут

def hash_text(text: str) -> str:
    """Создаем хеш текста для сравнения дубликатов"""
    return hashlib.md5(text.encode("utf-8")).hexdigest()

@client.on(events.NewMessage(chats=channels))
async def message_handler(event):
    message = event.message
    if not message.message and not message.media:
        return

    text = message.message.lower() if message.message else ''
    matched_keyword = next((kw for kw in keywords if kw in text), None)
    if not matched_keyword:
        return

    matched_exclude = next((kw for kw in exclude_keywords if kw in text), None)
    if matched_exclude:
        logging.info(f"[LOG] ❌ Исключение: {matched_exclude}")
        print(f"[LOG] ❌ Исключение: {matched_exclude}")
        return

    now = time.time()
    msg_hash = hash_text(text)
    if msg_hash in recent_messages and now - recent_messages[msg_hash] < DUPLICATE_TIMEOUT:
        logging.info(f"[LOG] ⚠️ Дубликат. Пропущено (повтор за {int(now - recent_messages[msg_hash])} сек).")
        print(f"[LOG] ⚠️ Дубликат. Пропущено (повтор за {int(now - recent_messages[msg_hash])} сек).")
        return
    recent_messages[msg_hash] = now

    try:
        sender = await event.get_chat()
        channel_name = getattr(sender, 'title', 'Неизвестный канал')

        channel_id = event.chat_id
        user_id = message.sender_id

        # Кликабельные ссылки
        user_link = f"[Пользователь](tg://user?id={user_id})"
        channel_link = f"[Канал](https://t.me/c/{str(channel_id)[4:]})" if str(channel_id).startswith("-100") else f"Канал ID: {channel_id}"
        reply_text = f"{channel_link}\n{user_link}"

        if message.grouped_id:
            # Пересылаем альбом как есть
            album = []
            async for m in client.iter_messages(event.chat_id, reverse=True, limit=40):
                if m.grouped_id == message.grouped_id:
                    album.append(m)
            if album:
                album = sorted(album, key=lambda m: m.id)
                await client.forward_messages(target_group, album)
                # Отправляем ответ к первому сообщению альбома
                await client.send_message(target_group, reply_text, reply_to=album[0].id, parse_mode='md')
                logging.info(f'✅ Переслан альбом из "{channel_name}" успешно.')
                print(f'✅ Переслан альбом из "{channel_name}" успешно.')
        else:
            # Пересылаем одно сообщение
            forwarded = await client.forward_messages(target_group, message)
            await client.send_message(target_group, reply_text, reply_to=forwarded.id, parse_mode='md')
            logging.info(f'✅ Переслано сообщение из "{channel_name}" успешно.')
            print(f'✅ Переслано сообщение из "{channel_name}" успешно.')

    except Exception as e:
        logging.error(f'❌ Ошибка пересылки: {e}')
        print(f'❌ Ошибка пересылки: {e}')


async def main():
    await client.start(phone=phone)
    logging.info("🤖 Бот запущен и слушает каналы...")
    print("🤖 Бот запущен и слушает каналы...")
    logging.info(f'🔍 Слушаем каналы: {", ".join(str(c) for c in channels)}')
    print(f'🔍 Слушаем каналы: {", ".join(str(c) for c in channels)}')
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())