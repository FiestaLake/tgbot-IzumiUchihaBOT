import html
from io import BytesIO
from typing import Optional

from telegram import Message, Update, User, Chat, ParseMode
from telegram.error import BadRequest, TelegramError
from telegram.ext import CommandHandler, MessageHandler, Filters
from telegram.utils.helpers import mention_html

import tg_bot.modules.sql.global_bans_sql as sql
from tg_bot import (
    dispatcher,
    CallbackContext,
    OWNER_ID,
    SUDO_USERS,
    SUPPORT_USERS,
    STRICT_GBAN,
)
from tg_bot.modules.helper_funcs.chat_status import user_admin, is_user_admin
from tg_bot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from tg_bot.modules.helper_funcs.filters import CustomFilters
from tg_bot.modules.helper_funcs.misc import send_to_list
from tg_bot.modules.sql.users_sql import get_all_chats

GBAN_ENFORCE_GROUP = 6

GBAN_ERRORS = {
    "Bots can't add new chat members",
    "Channel_private",
    "Chat not found",
    "Can't demote chat creator",
    "Chat_admin_required",
    "Group chat was deactivated",
    "Method is available for supergroup and channel chats only",
    "Method is available only for supergroups",
    "Need to be inviter of a user to kick it from a basic group",
    "Not enough rights to restrict/unrestrict chat member",
    "Not in the chat",
    "Only the creator of a basic group can kick group administrators",
    "Peer_id_invalid",
    "User is an administrator of the chat",
    "User_not_participant",
    "Reply message not found",
    "Can't remove chat owner",
}

UNGBAN_ERRORS = {
    "Bots can't add new chat members",
    "Channel_private",
    "Chat not found",
    "Can't demote chat creator",
    "Chat_admin_required",
    "Group chat was deactivated",
    "Method is available for supergroup and channel chats only",
    "Method is available only for supergroups",
    "Need to be inviter of a user to kick it from a basic group",
    "Not enough rights to restrict/unrestrict chat member",
    "Not in the chat",
    "Only the creator of a basic group can kick group administrators",
    "Peer_id_invalid",
    "User is an administrator of the chat",
    "User_not_participant",
    "Reply message not found",
    "User not found",
}


def gban(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    message = update.effective_message  # type: Optional[Message]
    user = update.effective_user  # type: Optional[User]
    user_id, reason = extract_user_and_text(message, args)

    if not user_id or int(user_id) == 777000 or int(user_id) == 1087968824:
        message.reply_text("You don't seem to be referring to a user.")
        return

    if int(user_id) in SUDO_USERS:
        message.reply_text("Now kiss each other!")
        return

    if int(user_id) in SUPPORT_USERS:
        message.reply_text(
            "OOOH someone's trying to gban a support user! *grabs popcorn*"
        )
        return

    if user_id == bot.id:
        message.reply_text("Lets gban myself why don't I? Good one.")
        return

    try:
        user_chat = bot.get_chat(user_id)
    except BadRequest as excp:
        message.reply_text(excp.message)
        return

    if user_chat.type != "private":
        message.reply_text("That's not a user!")
        return

    try:
        update.effective_chat.ban_member(user_id)
    except:
        pass

    if sql.is_user_gbanned(user_id):
        if not reason:
            message.reply_text(
                "This user is already gbanned; I'd change the reason, but you haven't given me one..."
            )
            return

        old_reason = sql.update_gban_reason(
            user_id, user_chat.username or user_chat.first_name, reason
        )
        user_id, new_reason = extract_user_and_text(message, args)
        if old_reason:
            banner = update.effective_user  # type: Optional[User]
            send_to_list(
                bot,
                SUDO_USERS + SUPPORT_USERS,
                "<b>Emendation of Global Ban</b>"
                "\n#GBAN"
                "\n<b>Status:</b> <code>Amended</code>"
                "\n<b>Sudo Admin:</b> {}"
                "\n<b>User:</b> {}"
                "\n<b>ID:</b> <code>{}</code>"
                "\n<b>Previous Reason:</b> {}"
                "\n<b>Amended Reason:</b> {}".format(
                    mention_html(banner.id, banner.first_name),
                    mention_html(
                        user_chat.id, user_chat.first_name or "Deleted Account"
                    ),
                    user_chat.id,
                    old_reason,
                    new_reason,
                ),
                html=True,
            )

            message.reply_text(
                "This user is already gbanned, for the following reason:\n"
                "<code>{}</code>\n"
                "I've gone and updated it with your new reason!".format(
                    html.escape(old_reason)
                ),
                parse_mode=ParseMode.HTML,
            )
        else:
            banner = update.effective_user  # type: Optional[User]
            send_to_list(
                bot,
                SUDO_USERS + SUPPORT_USERS,
                "<b>Emendation of Global Ban</b>"
                "\n#GBAN"
                "\n<b>Status:</b> <code>New reason</code>"
                "\n<b>Sudo Admin:</b> {}"
                "\n<b>User:</b> {}"
                "\n<b>ID:</b> <code>{}</code>"
                "\n<b>New Reason:</b> {}".format(
                    mention_html(banner.id, banner.first_name),
                    mention_html(
                        user_chat.id, user_chat.first_name or "Deleted Account"
                    ),
                    user_chat.id,
                    new_reason,
                ),
                html=True,
            )
            message.reply_text(
                "This user is already gbanned, but had no reason set; I've gone and updated it!"
            )

        return

    starting = "Initiating global ban for {}...".format(
        mention_html(user_chat.id, user_chat.first_name or "Deleted Account")
    )
    keyboard = []
    # message.reply_text(starting, reply_markup=keyboard, parse_mode=ParseMode.HTML)

    banner = update.effective_user  # type: Optional[User]
    send_to_list(
        bot,
        SUDO_USERS + SUPPORT_USERS,
        "<b>Global Ban</b>"
        "\n#GBAN"
        "\n<b>Status:</b> <code>Enforcing</code>"
        "\n<b>Sudo Admin:</b> {}"
        "\n<b>User:</b> {}"
        "\n<b>ID:</b> <code>{}</code>"
        "\n<b>Reason:</b> {}".format(
            mention_html(banner.id, banner.first_name),
            mention_html(user_chat.id, user_chat.first_name or "Deleted Account"),
            user_chat.id,
            reason or "No reason given",
        ),
        html=True,
    )

    sql.gban_user(user_id, user_chat.username or user_chat.first_name, reason)

    chats = get_all_chats()
    for chat in chats:
        chat_id = chat.chat_id

        # Check if this group has disabled gbans
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            bot.ban_chat_member(chat_id, user_id)
        except BadRequest as excp:
            if excp.message in GBAN_ERRORS:
                pass
            else:
                message.reply_text("Could not gban due to: {}".format(excp.message))
                send_to_list(
                    bot,
                    SUDO_USERS + SUPPORT_USERS,
                    "Could not gban due to: {}".format(excp.message),
                )
                sql.ungban_user(user_id)
                return
        except TelegramError:
            pass

    send_to_list(
        bot,
        SUDO_USERS + SUPPORT_USERS,
        "{} has been successfully gbanned!".format(
            mention_html(user_chat.id, user_chat.first_name or "Deleted Account")
        ),
        html=True,
    )
    message.reply_text("Person has been gbanned.")


def ungban(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    message = update.effective_message  # type: Optional[Message]

    user_id = extract_user(message, args)
    if not user_id or int(user_id) == 777000 or int(user_id) == 1087968824:
        message.reply_text("You don't seem to be referring to a user.")
        return

    user_chat = bot.get_chat(user_id)
    if user_chat.type != "private":
        message.reply_text("That's not a user!")
        return

    if not sql.is_user_gbanned(user_id):
        message.reply_text("This user is not gbanned!")
        return

    banner = update.effective_user  # type: Optional[User]

    # message.reply_text("{}, will be unbanned globally.".format(user_chat.first_name or "Deleted Account"))

    send_to_list(
        bot,
        SUDO_USERS + SUPPORT_USERS,
        "<b>Regression of Global Ban</b>"
        "\n#UNGBAN"
        "\n<b>Status:</b> <code>Ceased</code>"
        "\n<b>Sudo Admin:</b> {}"
        "\n<b>User:</b> {}"
        "\n<b>ID:</b> <code>{}</code>".format(
            mention_html(banner.id, banner.first_name),
            mention_html(user_chat.id, user_chat.first_name or "Deleted Account"),
            user_chat.id,
        ),
        html=True,
    )

    chats = get_all_chats()
    for chat in chats:
        chat_id = chat.chat_id

        # Check if this group has disabled gbans
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            member = bot.get_chat_member(chat_id, user_id)
            if member.status == "kicked":
                bot.unban_chat_member(chat_id, user_id)

        except BadRequest as excp:
            if excp.message in UNGBAN_ERRORS:
                pass
            else:
                message.reply_text("Could not un-gban due to: {}".format(excp.message))
                bot.send_message(
                    OWNER_ID, "Could not un-gban due to: {}".format(excp.message)
                )
                return
        except TelegramError:
            pass

    sql.ungban_user(user_id)

    send_to_list(
        bot,
        SUDO_USERS + SUPPORT_USERS,
        "{} has been unbanned globally!".format(
            mention_html(user_chat.id, user_chat.first_name or "Deleted Account")
        ),
        html=True,
    )

    message.reply_text("Person has been un-gbanned.")


def gbanlist(update: Update, context: CallbackContext):
    bot = context.bot
    banned_users = sql.get_gban_list()

    if not banned_users:
        update.effective_message.reply_text(
            "There aren't any gbanned users! You're kinder than I expected..."
        )
        return

    banfile = "Screw these guys.\n"
    for user in banned_users:
        banfile += "[x] {} - {}\n".format(user["name"], user["user_id"])
        if user["reason"]:
            banfile += "Reason: {}\n".format(user["reason"])

    with BytesIO(str.encode(banfile)) as output:
        output.name = "gbanlist.txt"
        update.effective_message.reply_document(
            document=output,
            filename="gbanlist.txt",
            caption="Here is the list of currently globally banned users.",
        )


def check_and_ban(update, user_id, should_message=True):
    if sql.is_user_gbanned(user_id):
        update.effective_chat.ban_member(user_id)
        if should_message:
            update.effective_message.reply_text(
                "This user was globally banned by my owner or one of my sudo/support users so it shouldn't be here!"
            )


def enforce_gban(update: Update, context: CallbackContext):
    bot = context.bot
    # Not using @restrict handler to avoid spamming - just ignore if cant gban.
    if (
        sql.does_chat_gban(update.effective_chat.id)
        and update.effective_chat.get_member(bot.id).can_restrict_members
    ):
        user = update.effective_user  # type: Optional[User]
        chat = update.effective_chat  # type: Optional[Chat]
        msg = update.effective_message  # type: Optional[Message]

        if user and not is_user_admin(chat, user.id):
            check_and_ban(update, user.id)
            return

        if msg.new_chat_members:
            new_members = update.effective_message.new_chat_members
            for mem in new_members:
                check_and_ban(update, mem.id)
            return

        if msg.reply_to_message:
            user = msg.reply_to_message.from_user  # type: Optional[User]
            if user and not is_user_admin(chat, user.id):
                check_and_ban(update, user.id, should_message=False)
                return


@user_admin
def gbanstat(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    if len(args) > 0:
        if args[0].lower() in ["on", "yes"]:
            sql.enable_gbans(update.effective_chat.id)
            update.effective_message.reply_text(
                "I've enabled gbans in this group. This will help protect you "
                "from spammers, unsavoury characters, and the biggest trolls."
            )
        elif args[0].lower() in ["off", "no"]:
            sql.disable_gbans(update.effective_chat.id)
            update.effective_message.reply_text(
                "I've disabled gbans in this group. GBans wont affect your users "
                "anymore. You'll be less protected from any trolls and spammers "
                "though!"
            )
    else:
        update.effective_message.reply_text(
            "Give me some arguments to choose a setting! on/off, yes/no!\n\n"
            "Your current setting is: {}\n"
            "When True, any gbans that happen will also happen in your group. "
            "When False, they won't, leaving you at the possible mercy of "
            "spammers.".format(sql.does_chat_gban(update.effective_chat.id))
        )


def __stats__():
    return "{} gbanned users.".format(sql.num_gbanned_users())


def __user_info__(user_id):
    is_gbanned = sql.is_user_gbanned(user_id)

    if int(user_id) in SUDO_USERS or int(user_id) in SUPPORT_USERS:
        text = "Globally banned: <b>No</b> (Immortal)"
    else:
        text = "Globally banned: <b>{}</b>"
        if is_gbanned:
            text = text.format("Yes")
            user = sql.get_gbanned_user(user_id)
            if user.reason:
                text += "\nReason: {}".format(html.escape(user.reason))
        else:
            text = text.format("No")

    return text


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return "This chat is enforcing *gbans*: `{}`.".format(sql.does_chat_gban(chat_id))


__help__ = """
*Admin only:*
 - /gbanstat <on/off/yes/no>: Will disable the effect of global bans on your group, or return your current settings.

Gbans, also known as global bans, are used by the bot owners to ban spammers across all groups. This helps protect \
you and your groups by removing spam flooders as quickly as possible. They can be disabled for you group by calling \
/gbanstat
"""

__mod_name__ = "Global Bans"

GBAN_HANDLER = CommandHandler(
    "gban",
    gban,
    run_async=True,
    filters=CustomFilters.sudo_filter | CustomFilters.support_filter,
)
UNGBAN_HANDLER = CommandHandler(
    "ungban",
    ungban,
    run_async=True,
    filters=CustomFilters.sudo_filter | CustomFilters.support_filter,
)
GBAN_LIST = CommandHandler(
    "gbanlist",
    gbanlist,
    filters=CustomFilters.sudo_filter | CustomFilters.support_filter,
)

GBAN_STATUS = CommandHandler(
    "gbanstat", gbanstat, run_async=True, filters=Filters.chat_type.groups
)

GBAN_ENFORCER = MessageHandler(
    Filters.all & Filters.chat_type.groups, enforce_gban, run_async=True
)

dispatcher.add_handler(GBAN_HANDLER)
dispatcher.add_handler(UNGBAN_HANDLER)
dispatcher.add_handler(GBAN_LIST)
dispatcher.add_handler(GBAN_STATUS)

if STRICT_GBAN:  # enforce GBANS if this is set
    dispatcher.add_handler(GBAN_ENFORCER, GBAN_ENFORCE_GROUP)
