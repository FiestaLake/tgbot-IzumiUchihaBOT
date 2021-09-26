#
# tg_bot - android [From 235a01c6d of dev branch]
# Copyright (c) 2019-2021, corsicanu
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

from bs4 import BeautifulSoup
from requests import get
from yaml import load, Loader

from telegram import Update, Message, ParseMode

from tg_bot import dispatcher, CallbackContext
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.github import getphh


GITHUB = "https://github.com"
DEVICES_DATA = "https://raw.githubusercontent.com/androidtrackers/certified-android-devices/master/by_device.json"


def phh(update: Update, context: CallbackContext):
    args = context.args
    msg = update.effective_message  # type: Optional[Message]

    index = int(args[0]) if args and args[0].isdigit() else 0
    text = getphh(index)

    msg.reply_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)


def magisk(update: Update, unused_context: CallbackContext):
    msg = update.effective_message  # type: Optional[Message]
    url = "https://raw.githubusercontent.com/topjohnwu/magisk-files/"

    releases = ""
    for type, branch in {
        "Stable": "master/stable",
        "Beta": "master/beta",
        "Canary": "master/canary",
    }.items():
        data = get(url + branch + ".json").json()
        notes = (
            "https://topjohnwu.github.io/Magisk/releases/"
            + data["magisk"]["versionCode"]
            + ".html"
        )
        if str(type) == "Canary":
            notes = "https://github.com/topjohnwu/magisk-files/blob/canary/notes.md"
        releases += (
            f'• {type} - <code>{data["magisk"]["version"]}'
            f'-{data["magisk"]["versionCode"]}</code> → '
            f'<a href="{notes}">Notes</a> / '
            f'<a href="{data["magisk"]["link"]}">Magisk</a>\n'
        )

    msg.reply_text(
        "<b>Latest Magisk Releases:</b>\n\n{}\n"
        "<a href='https://topjohnwu.github.io/Magisk/install.html'>"
        "Install/uninstall instruction</a>".format(releases),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


def device(update: Update, context: CallbackContext):
    args = context.args
    msg = update.effective_message  # type: Optional[Message]

    if not args:
        msg.reply_text("No codename provided.")
        return

    device = " ".join(args)
    db = get(DEVICES_DATA).json()
    try:
        reply = f"Search results for {device}:\n\n"
        brand = db[device][0]["brand"]
        name = db[device][0]["name"]
        model = db[device][0]["model"]
        codename = device
        reply += (
            f"<b>{brand} {name}</b>\n"
            f"Model: <code>{model}</code>\n"
            f"Codename: <code>{codename}</code>\n\n"
        )
    except KeyError:
        msg.reply_text(f"Couldn't find info about {device}!")
        return

    msg.reply_text(reply, parse_mode=ParseMode.HTML, disable_web_page_preview=True)


def getfw(update: Update, context: CallbackContext):
    args = context.args
    msg = update.effective_message  # type: Optional[Message]

    if not args:
        msg.reply_text("Provide a valid type!")
        return

    if args[0].lower() == "m":
        if len(args) < 2:
            msg.reply_text("Provide a valid codename!")
            return

        codename = args[1]
        URL = "https://raw.githubusercontent.com/XiaomiFirmwareUpdater/miui-updates-tracker/master/data/latest.yml"

        yaml_data = load(get(URL).content, Loader=Loader)
        data = [i for i in yaml_data if codename in i["codename"]]

        if not data:
            msg.reply_text("Provide a valid codename!")
            return

        fwreply = []
        for fw in data:
            android = fw["android"]
            branch = fw["branch"]
            method = fw["method"]
            link = fw["link"]
            fcodename = fw["codename"]
            version = fw["version"]

            text = f"{fcodename} | {version} ({android}, {branch}, {method})"
            fwreply.append(f"<a href='{link}'>{text}</a>\n")

        reply = f"<b>The latest firmwares for {codename}:</b>\n\n"
        fwreply.sort()
        for data in fwreply:
            reply += data

        msg.reply_text(
            reply,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return

    if args[0].lower() == "s":
        if len(args) < 3:
            msg.reply_text("Provide both valid model and CSC!")
            return

        temp, csc = args[1], args[2]
        model = "sm-" + temp if not temp.lower().startswith("sm-") else temp
        fota = get(
            f"http://fota-cloud-dn.ospserver.net/firmware/{csc.upper()}/{model.upper()}/version.xml"
        )
        test = get(
            f"http://fota-cloud-dn.ospserver.net/firmware/{csc.upper()}/{model.upper()}/version.test.xml"
        )
        if test.status_code != 200:
            msg.reply_text("Provide both valid model and CSC!")
            return

        url1 = f"https://samfrew.com/model/{model.upper()}/region/{csc.upper()}/"
        url2 = (
            f"https://www.sammobile.com/samsung/firmware/{model.upper()}/{csc.upper()}/"
        )
        url3 = f"https://sfirmware.com/samsung-{model.lower()}/#tab=firmwares"
        url4 = f"https://samfw.com/firmware/{model.upper()}/{csc.upper()}/"

        page1 = BeautifulSoup(fota.content, "lxml")
        page2 = BeautifulSoup(test.content, "lxml")
        os1 = page1.find("latest").get("o")
        os2 = page2.find("latest").get("o")
        data1 = page1.find("latest").text.strip()
        data2 = page2.find("latest").text.strip()
        reply = f"<b>The latest firmwares for "
        reply += f"{model.upper()} and {csc.upper()}:</b>\n\n"

        if data1:
            pda1, csc1, phone1 = data1.split("/")
            reply += "<b>Latest public firmware:</b>\n"
            reply += f"• PDA: <code>{pda1}</code>\n"
            reply += f"• CSC: <code>{csc1}</code>\n"
            if phone1:
                reply += f"• Phone: <code>{phone1}</code>\n"
            if os1:
                reply += f"• Android: <code>{os1}</code>\n"
            reply += "\n"
        else:
            reply += "<b>No public release found.</b>\n\n"

        if len(data2.split("/")) > 2:
            pda2, csc2, phone2 = data2.split("/")
            reply += "<b>Latest test firmware:</b>\n"
            reply += f"• PDA: <code>{pda2}</code>\n"
            reply += f"• CSC: <code>{csc2}</code>\n"
            if phone2:
                reply += f"• Phone: <code>{phone2}</code>\n"
            if os2:
                reply += f"• Android: <code>{os2}</code>\n"
            reply += "\n"
        else:
            if os2 and data2:
                reply += "<b>Latest test firmware:</b>\n"
                reply += f"• Hash: <code>{data2}</code>\n"
                reply += f"• Android: <code>{os2}</code>\n"
            else:
                reply += "<b>No test release found.</b>\n\n"

        reply += f"<b>Downloads</b>\n"
        reply += f"• <a href='{url1}'>samfrew.com</a>\n"
        reply += f"• <a href='{url2}'>sammobile.com</a>\n"
        reply += f"• <a href='{url3}'>sfirmware.com</a>\n"
        reply += f"• <a href='{url4}'>samfw.com</a>\n"

        msg.reply_text(
            reply,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return

    msg.reply_text("Provide a valid type!")


def shrp(update: Update, context: CallbackContext):
    args = context.args
    msg = update.effective_message  # type: Optional[Message]

    if not args:
        msg.reply_text("No codename provided.")
        return

    device = " ".join(args)
    sf = f"https://sourceforge.net/projects/shrp/files/{device}/"
    url = get(sf)
    if url.status_code == 404:
        msg.reply_text(f"Couldn't find a SHRP folder for {device}!")
        return

    reply = f"<b>Official SHRP Releases for {device}:</b>\n\n"
    db = get(DEVICES_DATA).json()
    try:
        brand = db[device][0]["brand"]
        name = db[device][0]["name"]
        reply += f"<b>{brand} {name}</b>\n"
    except KeyError:
        pass

    reply += f"<a href='{sf}'>Downloads</a>"
    msg.reply_text(
        reply,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


def twrp(update: Update, context: CallbackContext):
    args = context.args
    msg = update.effective_message  # type: Optional[Message]

    if not args:
        msg.reply_text("No codename provided.")
        return

    device = " ".join(args)
    url = get(f"https://eu.dl.twrp.me/{device}/")
    if url.status_code == 404:
        msg.reply_text(f"Couldn't find a TWRP folder for {device}!")
        return

    reply = f"<b>The latest Official TWRP release for {device}:</b>\n\n"
    db = get(DEVICES_DATA).json()
    try:
        brand = db[device][0]["brand"]
        name = db[device][0]["name"]
        reply += f"<b>{brand} {name}</b>\n"
    except KeyError:
        pass

    page = BeautifulSoup(url.content, "lxml")
    date = page.find("em").text.strip()
    reply += f"<b>Updated:</b> <code>{date}</code>\n"
    trs = page.find("table").find_all("tr")
    row = 2 if trs[0].find("a").text.endswith("tar") else 1

    for i in range(row):
        download = trs[i].find("a")
        dl_link = f"https://eu.dl.twrp.me{download['href']}"
        dl_file = download.text
        size = trs[i].find("span", {"class": "filesize"}).text
        reply += f"<a href='{dl_link}'>{dl_file}</a> - "
        reply += f"<code>{size}</code>\n"

    msg.reply_text(
        reply,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


__help__ = """
Are you in the groups with the topic of Android related groups?
Nice commands are here to help you there!

*User commands*:
 - /magisk - Gets the latest Magisk for Stable/Beta/Canary branch.
 - /phh `<count>`- Gets the phhusson's phh treble releases.\
 A higher count means an older release; latest (0) if count is not given.
 - /device `<codename>` - Gets basic information of an Android device for the given codename.
 - /twrp `<codename>` - Gets the latest TWRP for an Android device for the given codename.
 - /shrp `<codename>` - Gets the latest SHRP for an Android device for the given codename.
 - /getfw `<S/M>` - Gets firmware info & download links for Samsung (S) or MIUI (M) devices.
  -> `M` `<codename>` - Fill out this to use the cmd for MIUI devices.
  -> `S` `<model>` `<csc>` -\
 Fill out these to use the cmd for Samsung devices.
"""

__mod_name__ = "Android"

PHH_HANDLER = DisableAbleCommandHandler("phh", phh, run_async=True)
MAGISK_HANDLER = DisableAbleCommandHandler("magisk", magisk, run_async=True)
DEVICE_HANDLER = DisableAbleCommandHandler("device", device, run_async=True)
TWRP_HANDLER = DisableAbleCommandHandler("twrp", twrp, run_async=True)
SHRP_HANDLER = DisableAbleCommandHandler("shrp", shrp, run_async=True)
GETFW_HANDLER = DisableAbleCommandHandler("getfw", getfw, run_async=True)

dispatcher.add_handler(PHH_HANDLER)
dispatcher.add_handler(MAGISK_HANDLER)
dispatcher.add_handler(DEVICE_HANDLER)
dispatcher.add_handler(TWRP_HANDLER)
dispatcher.add_handler(SHRP_HANDLER)
dispatcher.add_handler(GETFW_HANDLER)
