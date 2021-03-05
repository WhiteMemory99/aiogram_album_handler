import asyncio
from dataclasses import dataclass
from typing import List

from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.middlewares import BaseMiddleware

bot = Bot(token="TOKEN_HERE")
dp = Dispatcher(bot)


@dataclass
class GroupItem:
    content_type: str
    file_id: str = None


class AlbumMiddleware(BaseMiddleware):
    album_data: dict = {}

    async def on_process_message(self, message: types.Message, data: dict):
        if message.media_group_id:
            item = GroupItem(content_type=message.content_type)
            if message.photo:
                item.file_id = message.photo[-1].file_id
            else:
                item.file_id = message[item.content_type].file_id

            if not self.album_data.get(message.media_group_id):
                self.album_data[message.media_group_id] = [item]
                await asyncio.sleep(0.3)
                message.conf["is_last"] = True
                data["album"] = self.album_data[message.media_group_id]
            else:
                self.album_data[message.media_group_id].append(item)
                raise CancelHandler()

    async def on_post_process_message(self, message: types.Message, result: dict, data: dict):
        if message.media_group_id and message.conf.get("is_last"):
            del self.album_data[message.media_group_id]


@dp.message_handler(lambda message: message.media_group_id, content_types=types.ContentType.ANY)
async def handle_albums(message: types.Message, album: List[GroupItem]):
    """
    Сюда придёт уже готовый альбом: фото, видео, аудио, документы.
    """
    media_group = types.MediaGroup()
    for item in album:
        try:
            media_group.attach({"media": item.file_id, "type": item.content_type})
        except ValueError:
            return await message.answer(
                "Aiogram 2.11.2 содержит баг с отправкой аудио/документ групп. Обновите напрямую с git."
            )

    await message.answer_media_group(media_group)


if __name__ == "__main__":
    dp.middleware.setup(AlbumMiddleware())
    executor.start_polling(dp, skip_updates=True)
