from requests import get

from telegram import Update

from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot import dispatcher, CallbackContext


def ud(update: Update, context: CallbackContext):
    bot = context.bot
    try:
        message = update.effective_message
        text = message.text[len("/ud ") :]
        results = get(f"http://api.urbandictionary.com/v0/define?term={text}").json()
        reply_text = f'Word: {text}\nDefinition: {results["list"][0]["definition"]}'
    except IndexError:
        reply_text = f"Word: {text}\nDefinition: 404 definition not found"
    return message.reply_text(reply_text)


__help__ = """
Type the word or expression you want to search use in Urban dictionary.

Usage:
 - /ud <keyword> 
 
i.e. `/ud telegram`
Word: Telegram 
Definition: A once-popular system of telecommunications, in which the sender would contact the telegram service and speak their [message] over the [phone]. The person taking the message would then send it, via a teletype machine, to a telegram office near the receiver's [address]. The message would then be hand-delivered to the addressee. From 1851 until it discontinued the service in 2006, Western Union was the best-known telegram service in the world.
 
"""

__mod_name__ = "Dictionary"

ud_handle = DisableAbleCommandHandler("ud", ud, run_async=True)

dispatcher.add_handler(ud_handle)
