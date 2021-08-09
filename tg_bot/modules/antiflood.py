import html
from typing import Optional

from telegram import Message, Chat, Update, User, ParseMode
from telegram.error import BadRequest
from telegram.ext import Filters, MessageHandler, CommandHandler
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher, CallbackContext
from tg_bot.modules.helper_funcs.chat_status import (
    is_user_admin,
    user_admin,
    can_restrict,
)
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.sql import antiflood_sql as sql
from tg_bot.modules.helper_funcs.perms import check_perms

FLOOD_GROUP = 3


@loggable
def check_flood(update: Update, context: CallbackContext) -> str:
    bot = context.bot
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]

    if (
        int(user.id) == 777000 or int(user.id) == 1087968824 or not user
    ):  # ignore channels
        return ""

    # ignore admins
    if is_user_admin(chat, user.id):
        sql.update_flood(chat.id, None)
        return ""

    should_ban = sql.update_flood(chat.id, user.id)
    if not should_ban:
        return ""

    soft_flood = sql.get_flood_strength(chat.id)
    if soft_flood:  # kick
        chat.unban_member(user.id)
        reply = "Wonderful, I don't like your flooding. Get out! {} has been kicked!".format(
            mention_html(user.id, user.first_name)
        )

    else:  # ban
        chat.ban_member(user.id)
        reply = "Frankly, I like to leave the flooding to natural disasters. {} has been banned!".format(
            mention_html(user.id, user.first_name)
        )
    try:
        msg.reply_text(reply, parse_mode=ParseMode.HTML)
        msg.delete()
        return (
            "<b>{}:</b>"
            "\n#FLOOD_CTL"
            "\n<b>User:</b> {}"
            "\nFlooded the group.".format(
                html.escape(chat.title), mention_html(user.id, user.first_name)
            )
        )

    except BadRequest:
        msg.reply_text(
            "I can't kick people here, give me permissions first! Until then, I'll disable anti-flood."
        )
        sql.set_flood(chat.id, 0)
        return (
            "<b>{}:</b>"
            "\n#INFO"
            "\nDon't have kick permissions, so automatically disabled anti-flood.".format(
                chat.title
            )
        )


@user_admin
@can_restrict
@loggable
def set_flood(update: Update, context: CallbackContext) -> str:
    bot, args = context.bot, context.args
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    if not check_perms(update, 1):
        return

    if len(args) >= 1:
        val = args[0].lower()
        if val in ("off", "no", "0"):
            sql.set_flood(chat.id, 0)
            message.reply_text("Anti-flood has been disabled.")

        elif val.isdigit():
            amount = int(val)
            if amount <= 0:
                sql.set_flood(chat.id, 0)
                message.reply_text("Anti-flood has been disabled.")
                return (
                    "<b>{}:</b>"
                    "\n#SETFLOOD"
                    "\n<b>Admin:</b> {}"
                    "\nDisabled Anti-flood.".format(
                        html.escape(chat.title), mention_html(user.id, user.first_name)
                    )
                )

            if amount < 1:
                message.reply_text(
                    "Anti-flood has to be either 0 (disabled) or least 1"
                )
                return ""
            sql.set_flood(chat.id, amount)
            message.reply_text(
                "Anti-flood has been updated and set to {}".format(amount)
            )
            return (
                "<b>{}:</b>"
                "\n#SETFLOOD"
                "\n<b>Admin:</b> {}"
                "\nSet anti-flood to <code>{}</code>.".format(
                    html.escape(chat.title),
                    mention_html(user.id, user.first_name),
                    amount,
                )
            )

        else:
            message.reply_text(
                "Unrecognised argument - please use a number, 'off', or 'no'."
            )
    else:
        message.reply_text(
            "Give me an argument! Set a number to enforce against consecutive spams.\n"
            "i.e `/setflood 5`: to control consecutive of messages.",
            parse_mode=ParseMode.MARKDOWN,
        )
    return ""


def flood(update: Update, context: CallbackContext):
    bot = context.bot
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]
    limit = sql.get_flood_limit(chat.id)
    if limit == 0:
        update.effective_message.reply_text(
            "I'm not currently enforcing flood control!"
        )
    else:
        soft_flood = sql.get_flood_strength(chat.id)
        if soft_flood:
            msg.reply_text(
                "I'm currently kicking users out if they send more than {} "
                "consecutive messages. They will able to join again!".format(
                    limit, parse_mode=ParseMode.MARKDOWN
                )
            )
        else:
            msg.reply_text(
                "I'm currently banning users if they send more than {} "
                "consecutive messages.".format(limit, parse_mode=ParseMode.MARKDOWN)
            )


@user_admin
@loggable
def set_flood_strength(update: Update, context: CallbackContext):
    if not check_perms(update, 1):
        return
    bot, args = context.bot, context.args
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]

    if args:
        if args[0].lower() in ("on", "yes"):
            sql.set_flood_strength(chat.id, False)
            msg.reply_text("Exceeding consecutive flood limit will result in a ban!")
            return (
                "<b>{}:</b>\n"
                "<b>• Admin:</b> {}\n"
                "Has enabled strong flood and users will be banned.".format(
                    html.escape(chat.title), mention_html(user.id, user.first_name)
                )
            )

        if args[0].lower() in ("off", "no"):
            sql.set_flood_strength(chat.id, True)
            msg.reply_text(
                "Exceeding consecutive flood limit will result in a kick, Users will able to join back."
            )
            return (
                "<b>{}:</b>\n"
                "<b>• Admin:</b> {}\n"
                "Has disabled strong flood and users will only be kicked.".format(
                    html.escape(chat.title), mention_html(user.id, user.first_name)
                )
            )
        msg.reply_text("I only understand on/yes/no/off!")
    else:
        soft_flood = sql.get_flood_strength(chat.id)
        if soft_flood is True:
            msg.reply_text(
                "Flood strength is currently set to *kick* users when they exceed the limits. ",
                parse_mode=ParseMode.MARKDOWN,
            )

        elif soft_flood:
            msg.reply_text(
                "The default configuration for flood control is currently set as a ban.",
                parse_mode=ParseMode.MARKDOWN,
            )

        elif soft_flood is False:
            msg.reply_text(
                "Flood strength is currently set to *ban* users when they exceed the limits, "
                "user will be banned.",
                parse_mode=ParseMode.MARKDOWN,
            )
    return ""


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    limit = sql.get_flood_limit(chat_id)
    soft_flood = sql.get_flood_strength(chat_id)
    if limit == 0:
        return "*Not* currently enforcing flood control."
    if soft_flood:
        return "Anti-flood is set to `{}` messages and *KICK* if exceeded.".format(
            limit
        )
    return "Anti-flood is set to `{}` messages and *BAN* if exceeded.".format(limit)


__help__ = """
You know how sometimes, people join, send 100 messages, and ruin your chat? With antiflood, that happens no more!

Antiflood allows you to take action on users that send more than x messages in a row. Exceeding the set flood \
will result in banning or kicking the user.

 - /flood: Get the current flood control setting

*Admin only:*
 - /setflood <int/'no'/'off'>: enables or disables flood control
 - /strongflood <on/yes/off/no>: If set to on, exceeding the flood limit will result in a ban. Else, will just kick.
"""

__mod_name__ = "Anti-Flood"

FLOOD_BAN_HANDLER = MessageHandler(
    Filters.all
    & ~Filters.status_update
    & Filters.chat_type.groups
    & ~Filters.update.edited_message,
    check_flood,
    run_async=True,
)
SET_FLOOD_HANDLER = CommandHandler(
    "setflood", set_flood, filters=Filters.chat_type.groups, run_async=True
)
FLOOD_HANDLER = CommandHandler(
    "flood", flood, filters=Filters.chat_type.groups, run_async=True
)
FLOOD_STRENGTH_HANDLER = CommandHandler(
    "strongflood", set_flood_strength, filters=Filters.chat_type.groups, run_async=True
)

dispatcher.add_handler(FLOOD_BAN_HANDLER, FLOOD_GROUP)
dispatcher.add_handler(SET_FLOOD_HANDLER)
dispatcher.add_handler(FLOOD_HANDLER)
dispatcher.add_handler(FLOOD_STRENGTH_HANDLER)
