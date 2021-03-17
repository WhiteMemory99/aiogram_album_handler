import asyncio
from dataclasses import dataclass
from typing import List

from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters import BoundFilter
from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.middlewares import BaseMiddleware

bot = Bot(token="TOKEN_HERE")  # Place your token here
dp = Dispatcher(bot)


@dataclass
class GroupItem:
    message_id: int
    content_type: str
    caption: str
    file_id: str = None


class IsMediaGroup(BoundFilter):
    """
    This filter checks if the message is part of a media group.

    `is_media_group=True` - the message is part of a media group
    `is_media_group=False` - the message is NOT part of a media group
    """

    key = "is_media_group"

    def __init__(self, is_media_group: bool):
        self.is_media_group = is_media_group

    async def check(self, message: types.Message) -> bool:
        return bool(message.media_group_id) is self.is_media_group


dp.filters_factory.bind(IsMediaGroup)


class AlbumMiddleware(BaseMiddleware):
    """This middleware is for capturing media groups."""

    album_data: dict = {}

    async def on_process_message(self, message: types.Message, data: dict):
        if not message.media_group_id:
            return

        item = GroupItem(
            message_id=message.message_id,
            content_type=message.content_type,
            caption=message.caption,
        )

        if message.photo:
            item.file_id = message.photo[-1].file_id
        else:
            item.file_id = message[item.content_type].file_id

        try:
            self.album_data[message.media_group_id].append(item)
            raise CancelHandler()  # Tell aiogram to cancel handler for this group element
        except KeyError:
            self.album_data[message.media_group_id] = [item]
            await asyncio.sleep(0.25)

            message.conf["is_last"] = True
            data["album"] = self.album_data[message.media_group_id]

    async def on_post_process_message(self, message: types.Message, result: dict, data: dict):
        """Clean up after handling our album."""
        if message.media_group_id and message.conf.get("is_last"):
            del self.album_data[message.media_group_id]


@dp.message_handler(is_media_group=True, content_types=types.ContentType.ANY)
async def handle_albums(message: types.Message, album: List[GroupItem]):
    """This handler will receive a complete album of any type."""
    media_group = types.MediaGroup()
    for item in album:
        try:
            # We can also add a caption to each file by specifying `"caption": "text"`
            # GroupItem object stores the caption of each element `item.caption`
            media_group.attach({"media": item.file_id, "type": item.content_type})
        except ValueError:
            return await message.answer(
                "Aiogram 2.11.2 and below doesn't support sending document/audio groups this way."
            )

    await message.answer_media_group(media_group)


if __name__ == "__main__":
    dp.middleware.setup(AlbumMiddleware())
    executor.start_polling(dp, skip_updates=True)
