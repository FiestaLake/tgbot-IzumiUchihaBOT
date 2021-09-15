#
# tg_bot - notes [From Upstream 6b1d961]
# Copyright (C) 2017-2019, Paul Larsen
# Copyright (c) 2019-2021, corsicanu
# Copyright (c) 2020-2021, soulr344
# Copyright (c) 2021, Sung Mingi a.k.a. FiestaLake
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

import re
import html
from io import BytesIO
from typing import Optional

from telegram import MAX_MESSAGE_LENGTH, ParseMode, InlineKeyboardMarkup
from telegram import Message, Update, Chat, User
from telegram.error import BadRequest
from telegram.ext import CommandHandler, RegexHandler, Filters, CallbackQueryHandler
from telegram.inline.inlinekeyboardbutton import InlineKeyboardButton
from telegram.utils.helpers import mention_html

import tg_bot.modules.sql.notes_sql as sql
from tg_bot import dispatcher, CallbackContext, LOGGER
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.helper_funcs.chat_status import user_admin
from tg_bot.modules.helper_funcs.misc import build_keyboard, revert_buttons
from tg_bot.modules.helper_funcs.upstream.msg_types import parse_note_type

WARNING = """
ID and Name of notes conflict each other.
Will use the note named with {} (not ID) this time.
A name only with numbers is not accepted anymore.
Please consider changing a name of it later!
"""

FILE_MATCHER = re.compile(r"^###file_id(!photo)?###:(.*?)(?:\s|$)")

ENUM_FUNC_MAP = {
    sql.Types.TEXT.value: dispatcher.bot.send_message,
    sql.Types.BUTTON_TEXT.value: dispatcher.bot.send_message,
    sql.Types.STICKER.value: dispatcher.bot.send_sticker,
    sql.Types.DOCUMENT.value: dispatcher.bot.send_document,
    sql.Types.PHOTO.value: dispatcher.bot.send_photo,
    sql.Types.AUDIO.value: dispatcher.bot.send_audio,
    sql.Types.VOICE.value: dispatcher.bot.send_voice,
    sql.Types.VIDEO.value: dispatcher.bot.send_video,
}


def get(bot, update, notename, show_none=True, no_format=False):
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]

    # Seperate process to get a note for given ID.
    if notename.isdecimal():
        check = sql.get_note(chat.id, notename)
        # Choose notename instead of noteid.
        if check:
            msg.reply_text(WARNING.format(notename=notename))
            note = check
        # Search notename for given noteid.
        else:
            note_list = sql.get_all_chat_notes(chat.id)
            if note_list[int(notename) - 1]:
                note = note_list[int(notename) - 1]
    else:
        note = sql.get_note(chat.id, notename)

    if note:
        # If a replied msg, reply to that msg.
        if msg.reply_to_message:
            reply = msg.reply_to_message
        else:
            reply = msg

        text = note.value
        keyb = []

        if note.md_ver == 1:
            parseMode = ParseMode.MARKDOWN
        elif note.md_ver == 2:
            parseMode = ParseMode.MARKDOWN_V2
        else:
            parseMode = ""

        buttons = sql.get_buttons(chat.id, note.name)
        if no_format:
            parseMode = None
            text += revert_buttons(buttons)
        else:
            keyb = build_keyboard(buttons)

        keyboard = InlineKeyboardMarkup(keyb)

        try:
            if note.msgtype in (sql.Types.BUTTON_TEXT, sql.Types.TEXT):
                bot.send_message(
                    chat.id,
                    text,
                    reply_to_message_id=reply.message_id,
                    parse_mode=parseMode,
                    disable_web_page_preview=True,
                    reply_markup=keyboard,
                )
            else:
                ENUM_FUNC_MAP[note.msgtype](
                    chat.id,
                    note.file,
                    caption=text,
                    reply_to_message_id=reply.message_id,
                    parse_mode=parseMode,
                    reply_markup=keyboard,
                )

        except BadRequest as excp:
            if excp.message == "Entity_mention_user_invalid":
                msg.reply_text(
                    "The user you want to mention hasn't seen by me yet."
                    "\nForward me one of their messages to mention them."
                )
            elif FILE_MATCHER.match(note.value):
                msg.reply_text(
                    "I couldn't send this note due to incorrectly imported files."
                    "\nI will remove the note. Save it again if you need it."
                )
                sql.rm_note(chat.id, note.name)
            else:
                msg.reply_text(
                    f"I couldn't send this note due to error: {excp.message}"
                )
                LOGGER.exception(
                    "Could not parse message #%s in chat %s", note.name, str(chat.id)
                )
                LOGGER.warning("Message was: %s", str(note.value))

        return

    if show_none:
        msg.reply_text("The note couldn't be found.")


def cmd_get(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    if len(args) >= 2 and args[1].lower() == "noformat":
        get(bot, update, args[0], show_none=True, no_format=True)
    elif len(args) >= 1:
        get(bot, update, args[0], show_none=True)
    else:
        update.effective_message.reply_text(
            "Please write down a correct name of the note."
        )


def hash_get(update: Update, context: CallbackContext):
    bot = context.bot
    message = update.effective_message.text
    fst_word = message.split()[0]
    no_hash = fst_word[1:]
    get(bot, update, no_hash, show_none=False)


@user_admin
def save(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]

    try:
        name, text, data_type, content, buttons = parse_note_type(msg)
    except IndexError:
        msg.reply_text("An empty note isn't allowed.")
        return

    if data_type is None:
        msg.reply_text("Provide a note content.")
        return

    if name.isdecimal():
        name = "'{}'".format(name)

    name = name.lower()
    sql.add_note_to_db(chat.id, name, text, data_type, buttons=buttons, file=content)

    msg.reply_text(
        "Successfully saved note `{}`\!".format(name),
        parse_mode=ParseMode.MARKDOWN_V2,
    )


@user_admin
def clear(update: Update, context: CallbackContext):
    args = context.args
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]

    if not args:
        msg.reply_text("Provide a name of note.")
        return
    notename = args[0]

    # Seperate process to get a note for given ID.
    if notename.isdecimal():
        check = sql.get_note(chat.id, notename)
        # Choose notename instead of noteid.
        if check:
            msg.reply_text(WARNING.format(notename=notename))
        # Search notename for given noteid.
        else:
            note_list = sql.get_all_chat_notes(chat.id)
            if note_list[int(notename) - 1]:
                notename = note_list[int(notename) - 1].name
            else:
                msg.reply_text("The note to clear couldn't be found.")

    if sql.rm_note(chat.id, notename):
        msg.reply_text(
            "Successfully deleted note `{}`\!".format(notename),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    msg.reply_text("The note to clear couldn't be found.")


@user_admin
@loggable
def clearall(update: Update, context: CallbackContext):
    bot = context.bot
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    query = update.callback_query

    if not chat.type in ("group", "supergroup"):
        msg.reply_text("This command is made to be used in groups!")
        return

    if query:
        try:
            if query.data == "clearall_yes":
                try:
                    for note in sql.get_all_chat_notes(chat.id):
                        sql.rm_note(chat.id, note.name)
                    text = "All notes have been deleted successfully."
                    query.edit_message_text(text)
                except BadRequest as excp:
                    if excp.message == "Chat_not_modified":
                        pass

                return (
                    "<b>{}:</b>"
                    "\n#ALL_NOTES_CLEARED"
                    "\n<b>Admin:</b> {}".format(
                        html.escape(chat.title), mention_html(user.id, user.first_name)
                    )
                )

            if query.data == "clearall_no":
                text = "Deleting all notes has been cancelled."
                query.edit_message_text(text)
                return ""

            # Ensure not to make a spin.
            bot.answer_callback_query(query.id)

        except BadRequest as excp:
            if excp.message in ("Message_not_modified", "Query_id_invalid"):
                pass
            else:
                LOGGER.exception("Exception in unpinall button. %s", str(query.data))

    keyboard = [
        InlineKeyboardButton(text="Yes", callback_data="clearall_yes"),
        InlineKeyboardButton(text="No", callback_data="clearall_no"),
    ]
    msg.reply_text(
        "Are you sure you want to delete ALL notes?" "\nThis action cannot be undone.",
        reply_markup=InlineKeyboardMarkup([keyboard]),
    )

    return ""


def list_notes(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]
    note_list = sql.get_all_chat_notes(chat.id)
    reply = "*Get notes* available in here\n"
    reply += "by adding the *ID* or *Name*\n"
    reply += "after doing `#` or `/get `\n\n"
    reply += "*ID*     *Name*\n"
    del_reply = reply
    count = 1

    for note in note_list:
        if count < 10:
            note_name = "`{}`\.      ".format(count) + "`{}`\n".format(note.name)
        if count >= 10 and count < 100:
            note_name = "`{}`\.    ".format(count) + "`{}`\n".format(note.name)
        if count >= 100:
            note_name = "`{}`\.  ".format(count) + "`{}`\n".format(note.name)
        if len(reply) + len(note_name) > MAX_MESSAGE_LENGTH:
            msg.reply_text(reply, parse_mode=ParseMode.MARKDOWN_V2)
            reply = ""
        reply += note_name
        count = count + 1

    if del_reply == reply:
        msg.reply_text("No notes in here!")
        return

    msg.reply_text(text=reply, parse_mode=ParseMode.MARKDOWN_V2)


def __import_data__(chat_id, data):
    failures = []
    for notename, notedata in data.get("extra", {}).items():
        match = FILE_MATCHER.match(notedata)

        if match:
            failures.append(notename)
            notedata = notedata[match.end() :].strip()
            if notedata:
                sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.TEXT)
        else:
            sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.TEXT)

    if failures:
        with BytesIO(str.encode("\n".join(failures))) as output:
            output.name = "failed_imports.txt"
            dispatcher.bot.send_document(
                chat_id,
                document=output,
                filename="failed_imports.txt",
                caption="These files/photos failed to import due to originating "
                "from another bot. This is a telegram API restriction, and can't "
                "be avoided. Sorry for the inconvenience!",
            )


def __stats__():
    return "{} notes, across {} chats.".format(sql.num_notes(), sql.num_chats())


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    notes = sql.get_all_chat_notes(chat_id)
    return "There are `{}` notes in this chat".format(len(notes))


__help__ = """
*Notes*

Save data for future users with notes!

Notes are great to save random tidbits of information; \
a phone number, a nice gif, a funny picture - anything!

*User commands*:
- /get `<notename/noteid>`: Get a note.
- `#<notename/noteid>`: Same as /get.

*Admin commands*:
- /save `<notename>` `<note text>`: \
Save a new note called "word". Replying to a message will save that message. \
Even works on media!
- /clear `<notename/noteid>`: Delete the associated note.
- /notes: List all notes in the group.
- /clearall: Delete all notes in the group.

*Tip*: To retrieve a note without the formatting, add `noformat` \
after /get `<notename/noteid>`.

*Tip 2*: Check /markdownhelp to see available markdowns.
"""

__mod_name__ = "Notes"

GET_HANDLER = CommandHandler(
    "get", cmd_get, run_async=True, filters=Filters.chat_type.groups
)
HASH_GET_HANDLER = RegexHandler(r"^#[^\s]+", hash_get, run_async=True)

SAVE_HANDLER = CommandHandler(
    "save", save, run_async=True, filters=Filters.chat_type.groups
)
DELETE_HANDLER = CommandHandler(
    "clear", clear, run_async=True, filters=Filters.chat_type.groups
)
DELETEALL_HANDLER = CommandHandler(
    "clearall", clearall, run_async=True, filters=Filters.chat_type.groups
)
HASH_DELETEALL_HANDLER = CallbackQueryHandler(
    pattern = r"clearall_",
    callback = clearall,
    run_async=True,
)
LIST_HANDLER = DisableAbleCommandHandler(
    ["notes", "saved"],
    list_notes,
    admin_ok=True,
    run_async=True,
    filters=Filters.chat_type.groups,
)


dispatcher.add_handler(GET_HANDLER)
dispatcher.add_handler(SAVE_HANDLER)
dispatcher.add_handler(LIST_HANDLER)
dispatcher.add_handler(DELETE_HANDLER)
dispatcher.add_handler(DELETEALL_HANDLER)
dispatcher.add_handler(HASH_DELETEALL_HANDLER)
dispatcher.add_handler(HASH_GET_HANDLER)
