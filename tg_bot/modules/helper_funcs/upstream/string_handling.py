#
# tg_bot - string_handling [From Upstream 6b1d961]
# Copyright (C) 2017-2019, Paul Larsen
# Copyright (C) 2015-2021 Leandro Toledo de Souza
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
import sys
from typing import Dict, Optional
import emoji

from telegram import MessageEntity
from telegram.utils.helpers import escape_markdown


"""
NOTE: the url \ escape may cause double escapes
# match * (bold) (don't escape if in url)
# match _ (italic) (don't escape if in url)
# match __ (underline) (don't escape if in url) - V2
# match ~ (strikethrough) (don't escape if in url) - V2
# match ` (code)
# match []() (markdown link)
# else, escape *, _, `, and [ in Markdown
# or, escape '_', '*', '[', ']', '(', ')', '~', '`',
  '>', '#', '+', '-', '=', '|', '{', '}', '.' and '!' in Markdown_V2
"""
MATCH_MD = re.compile(
    r"\*(.*?)\*|"
    r"_(.*?)_|"
    r"`(.*?)`|"
    r"(?<!\\)(\[.*?\])(\(.*?\))|"
    r"(?P<esc>[*_`\[])"
)

MATCH_MD_V2 = re.compile(
    r"\*(.*?)\*|"
    r"_(.*?)_|"
    r"__(.*?)__|"
    r"~(.*?)~|"
    r"`(.*?)`|"
    r"(?<!\\)(\[.*?\])(\(.*?\))|"
    r"(?P<esc>[_*\[\]()~`>#+-=|{}.!])"
)

# regex to find []() links -> hyperlinks/buttons
LINK_REGEX = re.compile(r"(?<!\\)\[.+?\]\((.*?)\)")
BTN_URL_REGEX = re.compile(r"(\[([^\[]+?)\]\(buttonurl:(?:/{0,2})(.+?)(:same)?\))")


def _selective_escape(to_parse: str, version: 1 = int) -> str:
    """
    Escape all invalid markdown

    Args:
        text (:obj:`str`): The text.
        version (:obj:`int` | :obj:`str`): Use to specify the version of telegrams Markdown.
            Either ``1`` or ``2``. Defaults to ``1``.

    :param to_parse: text to escape
    :return: valid markdown string
    """
    offset = 0  # Offset to be used as adding a \ character causes the string to shift.
    if int(version) == 1:
        regex = MATCH_MD
    elif int(version) == 2:
        regex = MATCH_MD_V2
    else:
        raise ValueError("Markdown version must be either 1 or 2!")

    for match in regex.finditer(to_parse):
        if match.group("esc"):
            ent_start = match.start()
            to_parse = (
                to_parse[: ent_start + offset] + "\\" + to_parse[ent_start + offset :]
            )
            offset += 1
    return to_parse


# This is a fun one.
def _calc_emoji_offset(to_calc) -> int:
    # Get all emoji in text.
    emoticons = emoji.get_emoji_regexp().finditer(to_calc)
    # Check the utf16 length of the emoji to determine the offset it caused.
    # Normal, 1 character emoji don't affect; hence sub 1.
    # special, eg with two emoji characters (eg face, and skin col) will have length 2, so by subbing one we
    # know we'll get one extra offset,
    return sum(len(e.group(0).encode("utf-16-le")) // 2 - 1 for e in emoticons)


def parse_markdown(
    txt: str,
    entities: Dict[MessageEntity, str] = None,
    buttoned: bool = False,
    version: int = 1,
    offset: int = 0,
) -> str:
    """
    Parse a string, escaping all invalid markdown entities.

    Escapes URL's so as to avoid URL mangling.
    Re-adds any telegram code entities obtained from the entities object.

    :param txt: text to parse
    :param entities: dict of message entities in text
    :param offset: message offset - command and notename length
    :return: valid markdown string
    """
    version = int(version)
    if version not in (1, 2):
        raise ValueError("Markdown version must be either 1 or 2!")
    if not entities:
        entities = {}
    if not txt:
        return ""

    prev = 0
    res = ""
    # Loop over all message entities, and:
    # reinsert code
    # escape free-standing urls
    for ent, ent_text in entities.items():
        if ent.offset < -offset:
            continue

        start = ent.offset + offset  # start of entity
        end = ent.offset + offset + ent.length - 1  # end of entity
        text = escape_markdown(ent_text, version)

        # count emoji to switch counter
        count = _calc_emoji_offset(txt[:start])
        start -= count
        end -= count

        if ent.type == "url":
            if version == 1:
                link = ent_text
            else:
                link = text
            res += _selective_escape(txt[prev:start], version) + f"[{link}]({ent_text})"

        elif ent.type == "text_link":
            if version == 1:
                url = ent.url
            else:
                # Links need special escaping. Also can't have entities nested within
                url = escape_markdown(ent.url, version=version, entity_type="text_link")
            res += _selective_escape(txt[prev:start], version) + "[{}]({})".format(
                text, url
            )

        elif ent.type == "text_mention" and ent.user.id:
            res += _selective_escape(
                txt[prev:start], version
            ) + "[{}](tg://user?id={})".format(text, ent.user.id)

        elif re.search(BTN_URL_REGEX, ent_text) and buttoned:
            res += _selective_escape(txt[prev:start], version) + ent_text

        elif ent.type == "bold":
            res += _selective_escape(txt[prev:start], version) + "*" + text + "*"

        elif ent.type == "italic":
            res += _selective_escape(txt[prev:start], version) + "_" + text + "_"

        elif ent.type == "code":
            res += (
                _selective_escape(txt[prev:start], version)
                + "`"
                + escape_markdown(ent_text, version=version, entity_type="code")
                + "`"
            )

        elif ent.type == "pre":
            code = escape_markdown(ent_text, version=version, entity_type="pre")
            if ent.language:
                prefix = "```" + ent.language + "\n"
            else:
                if code.startswith("\\"):
                    prefix = "```"
                else:
                    prefix = "```\n"

            res += _selective_escape(txt[prev:start], version) + prefix + code + "```"

        elif ent.type == "underline":
            if version == 1:
                raise ValueError(
                    "Underline entities are not supported for Markdown version 1"
                )
            res += _selective_escape(txt[prev:start], version) + "__" + text + "__"

        elif ent.type == "strikethrough":
            if version == 1:
                raise ValueError(
                    "Underline entities are not supported for Markdown version 1"
                )
            res += _selective_escape(txt[prev:start], version) + "~" + text + "~"

        else:
            res += _selective_escape(txt[prev:start], version) + text

        end += 1
        prev = end

    res += _selective_escape(txt[prev:], version)  # Add the rest of the text.
    return res


def parse_button_markdown(
    message_text: str,
    entities: Dict[MessageEntity, str] = None,
    version: int = 1,
    offset: int = 0,
) -> tuple("str, List"):
    version = int(version)
    markdown_note = parse_markdown(message_text, entities, True, version, offset)

    prev = 0
    note_data = ""
    buttons = []
    for match in BTN_URL_REGEX.finditer(markdown_note):
        # Check if btnurl is escaped
        n_escapes = 0
        to_check = match.start(1) - 1
        while to_check > 0 and markdown_note[to_check] == "\\":
            n_escapes += 1
            to_check -= 1

        # if even, not escaped -> create button
        if n_escapes % 2 == 0:
            # create a thruple with button label, url, and newline status
            buttons.append((match.group(2), match.group(3), bool(match.group(4))))
            note_data += markdown_note[prev : match.start(1)]
            prev = match.end(1)
        # if odd, escaped -> move along
        else:
            note_data += markdown_note[prev:to_check]
            prev = match.start(1) - 1

    note_data += markdown_note[prev:]

    return note_data, buttons
