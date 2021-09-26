#
# tg_bot - github [From d72236b of dev branch]
# Copyright (c) 2019-2021, corsicanu
# Copyright (c) 2019, Nuno Penim
# Copyright (c) 2020, HitaloSama
# Copyright (c) 2020-2021, soulr344
# Copyright (c) 2021, Sung Mingi a.k.a. FiestaLake
#
# Backported to 8b0d8866e of master branch.
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

from typing import Optional
from telegram.ext import CommandHandler, MessageHandler, Filters
from telegram import Chat, Message, Update, ParseMode, MAX_MESSAGE_LENGTH

import tg_bot.modules.helper_funcs.git_api as api
import tg_bot.modules.sql.github_sql as sql

from tg_bot import dispatcher, CallbackContext
from tg_bot.modules.helper_funcs.chat_status import user_admin
from tg_bot.modules.disable import DisableAbleCommandHandler


WARNING = """
ID and Name of repo shortcuts conflict each other!
Will use the repo named with {} (not ID) this time.

Number inside the name is not accepted anymore.
Please consider changing a name of it later!
"""


def getphh(index) -> str:
    recentRelease = api.getReleaseData(
        api.getData("phhusson/treble_experimentations"), index
    )
    if recentRelease is None:
        return "The specified release could not be found."

    author = api.getAuthor(recentRelease)
    authorUrl = api.getAuthorUrl(recentRelease)
    assets = api.getAssets(recentRelease)
    releaseName = api.getReleaseName(recentRelease)
    message = "<b>Author:</b> <a href='{}'>{}</a>\n".format(authorUrl, author)
    message += "<b>Release Name:</b> <code>" + releaseName + "</code>\n\n"
    message += "<b>Assets:</b>\n"

    for asset in assets:
        fileName = api.getReleaseFileName(asset)
        if fileName in ("manifest.xml", "patches.zip"):
            continue

        fileURL = api.getReleaseFileURL(asset)
        assetFile = "• <a href='{}'>{}</a>".format(fileURL, fileName)
        sizeB = ((api.getSize(asset)) / 1024) / 1024
        size = "{0:.2f}".format(sizeB)
        message += assetFile + "\n"
        message += "    <code>Size: " + size + " MB</code>\n"

    return message


def getData(url, index) -> str:
    if not api.getData(url):
        return "Invalid &lt;user&gt;/&lt;repo&gt; combo."
    recentRelease = api.getReleaseData(api.getData(url), index)
    if recentRelease is None:
        return "The specified release could not be found."

    author = api.getAuthor(recentRelease)
    authorUrl = api.getAuthorUrl(recentRelease)
    assets = api.getAssets(recentRelease)
    releaseName = api.getReleaseName(recentRelease)
    message = "<b>Author:</b> <a href='{}'>{}</a>\n".format(authorUrl, author)
    message += "<b>Release Name:</b> " + releaseName + "\n\n"

    for asset in assets:
        message += "<b>Asset:</b> \n"
        fileName = api.getReleaseFileName(asset)
        fileURL = api.getReleaseFileURL(asset)
        assetFile = "<a href='{}'>{}</a>".format(fileURL, fileName)
        sizeB = ((api.getSize(asset)) / 1024) / 1024
        size = "{0:.2f}".format(sizeB)
        downloadCount = api.getDownloadCount(asset)
        message += assetFile + "\n"
        message += "Size: " + size + " MB"
        message += "\nDownload Count: " + str(downloadCount) + "\n\n"

    return message


def getRepo(update, reponame):
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]

    # From notes module (dda0d97d14e545d06c2f1d4d11ed694dbb1c0b63).
    # Seperate process to get a shortcut for given ID.
    if reponame.isdecimal():
        check = sql.get_repo(chat.id, reponame)
        # Choose reponame instead of repoid.
        if check:
            msg.reply_text(WARNING.format(reponame))
            repo = check
        # Search reponame for given repoid.
        else:
            repos_list = sql.get_all_repos(chat.id)
            if repos_list[int(reponame) - 1]:
                repo = repos_list[int(reponame) - 1]
    else:
        repo = sql.get_repo(str(chat.id), reponame)

    if repo:
        return repo.value, repo.backoffset

    return None, None


def getRelease(update: Update, context: CallbackContext):
    args = context.args
    msg = update.effective_message  # type: Optional[Message]

    # To prevent args[int] failure.
    if len(args) < 1:
        msg.reply_text("Please use some arguments!")
        return

    # <name>/<repo> format is necessary.
    if "/" not in args[0]:
        msg.reply_text("Please specify a valid combination of <user>/<repo>!")
        return

    url = args[0]
    # index is 0 initally.
    index = 0
    if len(args) >= 2:
        # args[1] is index if it's specified.
        if args[1].isdigit():
            index = int(args[1])
        else:
            msg.reply_text("Please type a valid number!")
            return

    text = getData(url, index)
    msg.reply_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)


def hashFetch(update: Update, unused_context: CallbackContext):
    msg = update.effective_message  # type: Optional[Message]
    fst_word = msg.text.split()[0]
    no_hash = fst_word[1:]

    url, index = getRepo(update, no_hash)
    if url is None and index is None:
        msg.reply_text(
            "There was a problem parsing your request.\n"
            + "Likely this is not a saved repo shortcut.",
        )
        return

    text = getData(url, index)
    msg.reply_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)


def cmdFetch(update: Update, context: CallbackContext):
    args = context.args
    msg = update.effective_message  # type: Optional[Message]

    # To prevent args[int] failure.
    if len(args) < 1:
        msg.reply_text("Invalid repo name.")
        return

    url, index = getRepo(update, args[0])
    if url is None and index is None:
        msg.reply_text(
            "There was a problem parsing your request.\n"
            + "Likely this is not a saved repo shortcut.",
        )
        return

    text = getData(url, index)
    msg.reply_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)


def changelog(update: Update, context: CallbackContext):
    args = context.args
    msg = update.effective_message  # type: Optional[Message]

    # To prevent args[int] failure.
    if len(args) < 1:
        msg.reply_text("Please use some arguments!")
        return

    # Check database if args[0] is not <name>/<repo> format.
    if "/" not in args[0]:
        url, index = getRepo(update, args[0])
    # Assume args[0] is url if it is <name>/<repo> format.
    else:
        url = args[0]
        # index is 0 initally.
        index = 0
        if len(args) >= 2:
            # args[1] is index if it's specified.
            if args[1].isdigit():
                index = int(args[1])
            else:
                msg.reply_text("Please type a valid number!")
                return

    if not api.getData(url):
        msg.reply_text("Invalid repo.")
        return

    data = api.getData(url)
    release = api.getReleaseData(data, index)
    body = api.getBody(release)
    msg.reply_text(body)


@user_admin
def saveRepo(update: Update, context: CallbackContext):
    args = context.args
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]

    if len(args) < 2 or not (  # We need args[0] and args[1].
        "/" in args[1]
    ):  # This format is necessary to be saved.
        msg.reply_text(
            "Invalid data\.\n"
            + "Use `<reponame>` `<user>/<repo>` `<number (optional)>`\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    # From notes module.
    # Always save repo in lowercase.
    reponame = args[0].lower()
    # Avoid conflicts with repoid.
    if reponame.isnumeric():
        reponame = "'{}'".format(reponame)

    # index is 0 initally.
    index = 0
    if len(args) >= 3:
        # args[2] is index if it's specified.
        if args[2].isdigit():
            index = int(args[2])
        else:
            msg.reply_text("Please type a valid number!")
            return

    sql.add_repo_to_db(str(chat.id), reponame, args[1], index)
    msg.reply_text(
        "Repo shortcut `{}` saved successfully\!".format(reponame),
        parse_mode=ParseMode.MARKDOWN_V2,
    )


@user_admin
def delRepo(update: Update, context: CallbackContext):
    args = context.args
    chat = update.effective_chat  # type: Optional[Chat]
    msg = update.effective_message  # type: Optional[Message]

    # To prevent args[int] failure.
    if len(args) < 1:
        msg.reply_text("Invalid repo name.")
        return

    # From notes module (dda0d97d14e545d06c2f1d4d11ed694dbb1c0b63).
    # Seperate process to get a shortcut for given ID.
    reponame = args[0]
    if reponame.isdecimal():
        check = sql.get_repo(chat.id, reponame)
        # Choose reponame instead of repoid.
        if check:
            msg.reply_text(WARNING.format(reponame))
        # Search reponame for given repoid.
        else:
            repos_list = sql.get_all_repos(chat.id)
            if repos_list[int(reponame) - 1]:
                reponame = repos_list[int(reponame) - 1].name

    if sql.rm_repo(str(chat.id), reponame):
        msg.reply_text(
            "Repo shortcut `{}` deleted successfully\!".format(reponame),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    else:
        msg.reply_text(
            "Repo shortcut deletion failed\!\n"
            + "Maybe an unknown shortcut\? [`{}`]".format(reponame),
            parse_mode=ParseMode.MARKDOWN_V2,
        )


def listRepo(update: Update, unused_context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    repo_list = sql.get_all_repos(str(chat.id))
    msg = "*Get available repo shortcuts*\n"
    msg += "by adding the *ID* or *Name*\n"
    msg += "after typing `&` or `/fetch `\n\n"
    msg += "*ID*     *Name*\n"
    delmsg = msg
    count = 1

    # From notes module.
    for repo in repo_list:
        # Reduce space by the length of repoID.
        if count < 10:
            repo_name = "`{}`\.      ".format(count) + "`{}`\n".format(repo.name)
        if 10 <= count < 100:
            repo_name = "`{}`\.    ".format(count) + "`{}`\n".format(repo.name)
        if count >= 100:
            repo_name = "`{}`\.  ".format(count) + "`{}`\n".format(repo.name)
        # If msg + repo_name exceeds the maximum msg length on TG,
        # send the existing msg first, and then make a new msg again.
        if len(msg) + len(repo_name) > MAX_MESSAGE_LENGTH:
            update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)
            msg = ""
        msg += repo_name
        count = count + 1

    # delmsg == msg means there's no note available.
    if delmsg == msg:
        update.effective_message.reply_text("No repo shortcuts in this chat!")
        return

    update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)


def getVer(update: Update, unused_context: CallbackContext):
    msg = update.effective_message  # type: Optional[Message]
    ver = api.vercheck()
    msg.reply_text("GitHub API version: " + ver)


__help__ = """
*GitHub*

This module will help you to fetch GitHub releases.

*User commands:*
 - /git `<user>/<repo>`: Fetch the latest release from the given repo.
 - /git `<user>/<repo>` `<number>`: Fetch releases in past.
 - /fetch `<reponame>`: Fetch a saved repo shortcut.
 - `&reponame`: Same as /fetch.
 - /listrepo: Lists all repo shortcuts in chat.
 - /listrepos: Same as /listrepo
 - /gitver: Returns the current API version.
 - /changelog `<reponame>`: Gets the changelog of a saved repo shortcut.
 
*Admin commands:*
 - /saverepo `<name>` `<user>/<repo>`: Saves a repo value as shortcut.
 - /saverepo `<name>` `<user>/<repo>` `<number>`: Saves a repo shortcut in past.
 - /delrepo `<name>`: Deletes a repo shortcut.
"""

__mod_name__ = "GitHub"

RELEASE_HANDLER = DisableAbleCommandHandler(
    "git", getRelease, run_async=True, admin_ok=True
)
FETCH_HANDLER = DisableAbleCommandHandler(
    "fetch", cmdFetch, run_async=True, admin_ok=True, filters=Filters.chat_type.groups
)
SAVEREPO_HANDLER = CommandHandler(
    "saverepo", saveRepo, run_async=True, filters=Filters.chat_type.groups
)
DELREPO_HANDLER = CommandHandler(
    "delrepo", delRepo, run_async=True, filters=Filters.chat_type.groups
)
LISTREPO_HANDLER = DisableAbleCommandHandler(
    ["listrepo", "listrepos"],
    listRepo,
    admin_ok=True,
    run_async=True,
    filters=Filters.chat_type.groups,
)
VERCHECKER_HANDLER = DisableAbleCommandHandler(
    "gitver", getVer, admin_ok=True, run_async=True
)
CHANGELOG_HANDLER = DisableAbleCommandHandler(
    "changelog",
    changelog,
    run_async=True,
    admin_ok=True,
    filters=Filters.chat_type.groups,
)

HASHFETCH_HANDLER = MessageHandler(Filters.regex(r"^&[^\s]+"), hashFetch)

dispatcher.add_handler(RELEASE_HANDLER)
dispatcher.add_handler(FETCH_HANDLER)
dispatcher.add_handler(SAVEREPO_HANDLER)
dispatcher.add_handler(DELREPO_HANDLER)
dispatcher.add_handler(LISTREPO_HANDLER)
dispatcher.add_handler(HASHFETCH_HANDLER)
dispatcher.add_handler(VERCHECKER_HANDLER)
dispatcher.add_handler(CHANGELOG_HANDLER)
