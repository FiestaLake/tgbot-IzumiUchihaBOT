import html
import re
from typing import Optional

from telegram import Message, User, Chat, Update, ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, MessageHandler, Filters

import tg_bot.modules.sql.blacklist_sql as sql
from tg_bot import dispatcher, CallbackContext, LOGGER
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import user_admin, user_not_admin
from tg_bot.modules.helper_funcs.extraction import extract_text
from tg_bot.modules.helper_funcs.misc import split_message
from tg_bot.modules.helper_funcs.perms import check_perms

BLACKLIST_GROUP = 11

BASE_BLACKLIST_STRING = "The following blacklist filters are currently active in {}:\n"


def blacklist(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    chat_name = chat.title or chat.first or chat.username
    all_blacklisted = sql.get_chat_blacklist(chat.id)

    filter_list = BASE_BLACKLIST_STRING

    if len(args) > 0 and args[0].lower() == "copy":
        for trigger in all_blacklisted:
            filter_list += "<code>{}</code>\n".format(html.escape(trigger))
    else:
        for trigger in all_blacklisted:
            filter_list += " • <code>{}</code>\n".format(html.escape(trigger))

    split_text = split_message(filter_list)
    for text in split_text:
        if text == BASE_BLACKLIST_STRING:
            msg.reply_text("There are no blacklisted messages here!")
            return
        msg.reply_text(text.format(chat_name), parse_mode=ParseMode.HTML)


@user_admin
def add_blacklist(update: Update, context: CallbackContext):
    if not check_perms(update, 1):
        return
    bot = context.bot
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    words = msg.text.split(None, 1)

    if len(words) > 1:
        text = words[1]
        if "**" in text:
            msg.reply_text(
                "Can't set blacklist, please don't use consecutive multiple \"*\"."
            )
            return
        to_blacklist = list(
            {trigger.strip() for trigger in text.split("\n") if trigger.strip()}
        )
        for trigger in to_blacklist:
            sql.add_to_blacklist(chat.id, trigger.lower())

        if len(to_blacklist) == 1:
            msg.reply_text(
                "Added <code>{}</code> to the blacklist!".format(
                    html.escape(to_blacklist[0])
                ),
                parse_mode=ParseMode.HTML,
            )

        else:
            msg.reply_text(
                "Added <code>{}</code> triggers to the blacklist.".format(
                    len(to_blacklist)
                ),
                parse_mode=ParseMode.HTML,
            )

    else:
        msg.reply_text("Tell me which words you would like to add to the blacklist.")


@user_admin
def unblacklist(update: Update, context: CallbackContext):
    if not check_perms(update, 0):
        return
    bot = context.bot
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    words = msg.text.split(None, 1)

    if len(words) > 1:
        text = words[1]
        to_unblacklist = list(
            {trigger.strip() for trigger in text.split("\n") if trigger.strip()}
        )
        successful = 0
        for trigger in to_unblacklist:
            success = sql.rm_from_blacklist(chat.id, trigger.lower())
            if success:
                successful += 1

        if len(to_unblacklist) == 1:
            if successful:
                msg.reply_text(
                    "Removed <code>{}</code> from the blacklist!".format(
                        html.escape(to_unblacklist[0])
                    ),
                    parse_mode=ParseMode.HTML,
                )
            else:
                msg.reply_text("This isn't a blacklisted trigger...!")

        elif successful == len(to_unblacklist):
            msg.reply_text(
                "Removed <code>{}</code> triggers from the blacklist.".format(
                    successful
                ),
                parse_mode=ParseMode.HTML,
            )

        elif not successful:
            msg.reply_text(
                "None of these triggers exist, so they weren't removed.".format(
                    successful, len(to_unblacklist) - successful
                ),
                parse_mode=ParseMode.HTML,
            )

        else:
            msg.reply_text(
                "Removed <code>{}</code> triggers from the blacklist. {} did not exist, "
                "so were not removed.".format(
                    successful, len(to_unblacklist) - successful
                ),
                parse_mode=ParseMode.HTML,
            )
    else:
        msg.reply_text(
            "Tell me which words you would like to remove from the blacklist."
        )


@user_not_admin
def del_blacklist(update: Update, context: CallbackContext):
    bot = context.bot
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]
    to_match = extract_text(message)
    user = update.effective_user  # type: Optional[User]

    if not user.id or int(user.id) == 777000 or int(user.id) == 1087968824:
        return ""

    if not to_match:
        return

    chat_filters = sql.get_chat_blacklist(chat.id)
    for trigger in chat_filters:
        pattern = (
            r"( |^|[^\w])"
            + re.escape(trigger).replace(r"\*", "(.*)").replace(r"\\(.*)", "*")
            + r"( |$|[^\w])"
        )
        if re.search(pattern, to_match, flags=re.IGNORECASE):
            try:
                message.delete()
            except BadRequest as excp:
                if excp.message == "Message to delete not found":
                    pass
                else:
                    LOGGER.exception("Error while deleting blacklist message.")
            break


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    blacklisted = sql.num_blacklist_chat_filters(chat_id)
    return "There are {} blacklisted words.".format(blacklisted)


def __stats__():
    return "{} blacklist triggers, across {} chats.".format(
        sql.num_blacklist_filters(), sql.num_blacklist_filter_chats()
    )


__mod_name__ = "Blacklists"

__help__ = """
Blacklists are used to stop certain triggers from being said in a group. Any time the trigger is mentioned, \
the message will immediately be deleted. A good combo is sometimes to pair this up with warn filters!

Please check /regexhelp for how to setup proper triggers.

*NOTE:* blacklists do not affect group admins.

 - /blacklist: View the current blacklisted words.

*Admin only:*
 - /addblacklist <triggers>: Add a trigger to the blacklist. Each line is considered one trigger, so using different \
lines will allow you to add multiple triggers.
 - /unblacklist <triggers>: Remove triggers from the blacklist. Same newline logic applies here, so you can remove \
multiple triggers at once.
 - /rmblacklist <triggers>: Same as above.
 
Tip: To copy list of saved blacklist simply use `/blacklist copy`, the bot will send non-bulleted list of blacklist.
"""

BLACKLIST_HANDLER = DisableAbleCommandHandler(
    "blacklist",
    blacklist,
    filters=Filters.chat_type.groups,
    pass_args=True,
    admin_ok=True,
    run_async=True,
)
ADD_BLACKLIST_HANDLER = CommandHandler(
    "addblacklist", add_blacklist, filters=Filters.chat_type.groups, run_async=True
)
UNBLACKLIST_HANDLER = CommandHandler(
    ["unblacklist", "rmblacklist"],
    unblacklist,
    filters=Filters.chat_type.groups,
    run_async=True,
)
BLACKLIST_DEL_HANDLER = MessageHandler(
    (Filters.text | Filters.command | Filters.sticker | Filters.photo)
    & Filters.chat_type.groups,
    del_blacklist,
    run_async=True,
)

dispatcher.add_handler(BLACKLIST_HANDLER)
dispatcher.add_handler(ADD_BLACKLIST_HANDLER)
dispatcher.add_handler(UNBLACKLIST_HANDLER)
dispatcher.add_handler(BLACKLIST_DEL_HANDLER, group=BLACKLIST_GROUP)
