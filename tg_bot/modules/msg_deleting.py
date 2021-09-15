import datetime as dt
import html
import time
from typing import Optional

from telegram import Message, Chat, Update, User, ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters
from telegram.utils.helpers import mention_html

from tg_bot import LOGGER, dispatcher, CallbackContext
from tg_bot.modules.helper_funcs.chat_status import (
    bot_admin,
    user_admin,
    bot_can_delete,
)
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.helper_funcs.perms import check_perms


@user_admin
@bot_admin
@bot_can_delete
@loggable
def purge(update: Update, context: CallbackContext) -> str:
    if not check_perms(update, 0):
        return ""
    bot, args = context.bot, context.args
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    reply_msg = msg.reply_to_message
    now = dt.datetime.now(dt.timezone.utc)

    if reply_msg:
        if reply_msg.date > now - dt.timedelta(2):
            message_id = reply_msg.message_id
            delete_to = msg.message_id - 1
            if args and args[0].isdigit():
                new_del = message_id + int(args[0])
                # No point deleting messages which haven't been written yet.
                if new_del < delete_to:
                    delete_to = new_del

            for m_id in range(
                delete_to, message_id - 1, -1
            ):  # Reverse iteration over message ids
                try:
                    bot.deleteMessage(chat.id, m_id)
                except BadRequest as err:
                    if not err.message in (
                        "Message to delete not found",
                        "Message can't be deleted",
                    ):
                        purge_err = err.message
                        LOGGER.exception(err)
                        break

            try:
                msg.delete()
            except BadRequest as err:
                if err.message in (
                    "Message to delete not found",
                    "Message can't be deleted",
                ):
                    pass

            fin_text = "Purge complete\."
            if "purge_err" in locals():
                fin_text += (
                    f"\nI couldn't delete some messages\.\nLast error: `{purge_err}`"
                )

            del_msg = bot.send_message(
                chat.id, fin_text, parse_mode=ParseMode.MARKDOWN_V2
            )
            time.sleep(10)
            try:
                del_msg.delete()
            except BadRequest as err:
                if err.message in (
                    "Message to delete not found",
                    "Message can't be deleted",
                ):
                    pass

            return (
                "<b>{}:</b>"
                "\n#PURGE"
                "\n<b>Admin:</b> {}"
                "\nPurged <code>{}</code> messages.".format(
                    html.escape(chat.title),
                    mention_html(user.id, user.first_name),
                    delete_to - message_id,
                )
            )

        msg.reply_text(
            "I can't purge messages over two days old.\n"
            "Please choose a more recent message."
        )
        return ""

    msg.reply_text("Reply to a message where to purge from.")
    return ""


@user_admin
@bot_admin
@bot_can_delete
@loggable
def del_message(update: Update, context: CallbackContext) -> str:
    if not check_perms(update, 0):
        return ""
    msg = update.effective_message  # type: Optional[Message]
    reply_msg = msg.reply_to_message

    if reply_msg:
        try:
            reply_msg.delete()
        except BadRequest as err:
            msg.reply_text("I couldn't delete a message.")
            return ""

        try:
            msg.delete()
        except BadRequest as err:
            if err.message in (
                "Message to delete not found",
                "Message can't be deleted",
            ):
                pass

        return ""

    msg.reply_text("Reply to a message to delete.")
    return ""


__help__ = """
*Purges*

Deleting lots of messages is now easier than ever with purges!

*Admin commands:*
 - /del: Deletes the replied to message.
 - /purge: Delete all messages from the replied to message, to the current message.
 - /purge `<integer X>`: Delete the following X messages after the replied to message.
"""

__mod_name__ = "Purges"

DELETE_HANDLER = CommandHandler(
    "del", del_message, filters=Filters.chat_type.groups, run_async=True
)
PURGE_HANDLER = CommandHandler(
    "purge", purge, filters=Filters.chat_type.groups, run_async=True
)

dispatcher.add_handler(DELETE_HANDLER)
dispatcher.add_handler(PURGE_HANDLER)
