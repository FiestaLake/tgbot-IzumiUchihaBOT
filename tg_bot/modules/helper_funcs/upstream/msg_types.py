#
# tg_bot - msg_types [From d72236b of dev branch]
# Copyright (C) 2017-2019, Paul Larsen
# Copyright (c) 2019-2021, corsicanu
# Copyright (c) 2020-2021, soulr344
# Copyright (c) 2021, Sung Mingi a.k.a. FiestaLake
#
# Backported to c3f098a of master branch.
# Some functions may still be remained / not backported as legacy.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

from enum import IntEnum, unique

from telegram import Message
from telegram.utils.helpers import escape_markdown

from tg_bot.modules.helper_funcs.upstream.string_handling import parse_button_markdown


@unique
class Types(IntEnum):
    TEXT = 0
    BUTTON_TEXT = 1
    STICKER = 2
    DOCUMENT = 3
    PHOTO = 4
    AUDIO = 5
    VOICE = 6
    VIDEO = 7


def parse_note_type(msg: Message):
    data_type = None
    content = None
    text = ""
    buttons = []

    raw_text = msg.text or msg.caption
    args = raw_text.split(None, 2)
    note_name = args[1]

    if msg.reply_to_message:
        msg = msg.reply_to_message
        if msg.text or msg.caption:
            note_text = msg.text or msg.caption
        else:
            note_text = ""
        isReply = True
    else:
        if len(args) >= 3:
            note_text = str(args[2])
        else:
            note_text = ""
        isReply = False

    entities = msg.parse_entities() or msg.parse_caption_entities()
    if not isReply and note_text:
        offset = len(note_text) - len(raw_text)
    else:
        offset = 0

    if msg.sticker:
        # Sticker can't have text in the replied.
        sender_text = args[2] if len(args) >= 3 else ""
        buttons = parse_button_markdown(
            sender_text, entities, 2, offset
        )[1]
        content = msg.sticker.file_id
        data_type = Types.STICKER

    elif msg.document:
        content = msg.document.file_id
        text, buttons = parse_button_markdown(
            note_text, entities, 2, offset
        )
        data_type = Types.DOCUMENT

    elif msg.photo:
        content = msg.photo[-1].file_id  # last elem = best quality
        text, buttons = parse_button_markdown(
            note_text, entities, 2, offset
        )
        data_type = Types.PHOTO

    elif msg.audio:
        content = msg.audio.file_id
        text, buttons = parse_button_markdown(
            note_text, entities, 2, offset
        )
        data_type = Types.AUDIO

    elif msg.voice:
        content = msg.voice.file_id
        text, buttons = parse_button_markdown(
            note_text, entities, 2, offset
        )
        data_type = Types.VOICE

    elif msg.video:
        content = msg.video.file_id
        text, buttons = parse_button_markdown(
            note_text, entities, 2, offset
        )
        data_type = Types.VIDEO

    elif msg.text:  # For safety, do not allow caption when saving text only.
        text, buttons = parse_button_markdown(
            note_text, entities, 2, offset
        )
        if len(text.strip()) == 0:
            text = escape_markdown(note_name, 2)

        if buttons:
            data_type = Types.BUTTON_TEXT
        else:
            data_type = Types.TEXT

    return note_name, text, data_type, content, buttons
