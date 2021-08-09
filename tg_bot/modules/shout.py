from telegram import Update

from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.filters import CustomFilters
from tg_bot import dispatcher, CallbackContext


def shout(update: Update, context: CallbackContext):
    args = context.args
    msg = "```"
    text = " ".join(args)
    result = []
    result.append(" ".join(list(text)))
    for pos, symbol in enumerate(text[1:]):
        result.append(symbol + " " + "  " * pos + symbol)
    result = list("\n".join(result))
    result[0] = text[0]
    result = "".join(result)
    msg = "```\n" + result + "```"
    return update.effective_message.reply_text(msg, parse_mode="MARKDOWN")


# __help__ = """
# A little piece of fun wording! Give a loud shout out in the chatroom.
#
# i.e /shout HELP, bot replies with huge coded HELP letters within the square.
#
# - /shout <keyword>: write anything you want to give loud shout.
#    ```
#    t e s t
#    e e
#    s   s
#    t     t
#    ```
# """

__mod_name__ = "Shout"

SHOUT_HANDLER = DisableAbleCommandHandler(
    "shout", shout, filters=CustomFilters.support_filter, run_async=True
)

dispatcher.add_handler(SHOUT_HANDLER)
