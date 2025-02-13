from datetime import datetime as dt

from pyrogram.filters import regex
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputMediaVideo,
)

from bot import bot, pyro_errors
from bot.utils.bot_utils import get_json
from bot.utils.log_utils import logger
from bot.utils.msg_utils import (
    chat_is_allowed,
    download_media_to_memory,
    user_is_allowed,
    user_is_privileged,
)

meme_list = []


async def gen_meme(link, pm=False):
    i = 1
    while True:
        result = await get_json(link)
        _id = result.get("ups")
        title = result.get("title")
        if not title:
            return None, None, None, None
        author = result.get("author")
        pl = result.get("postLink")
        if i > 100:
            raise Exception("Request Timeout!")
        i += 1
        if pl in meme_list:
            continue
        if len(meme_list) > 10000:
            meme_list.clear()
        nsfw = result.get("nsfw")
        if bot.block_nsfw and nsfw and not pm:
            return None, None, None, True
        meme_list.append(pl)
        sb = result.get("subreddit")
        nsfw_text = "**🔞 NSFW**\n"
        caption = f"{nsfw_text if nsfw else str()}**{title.strip()}**\n{pl}\n\nBy u/{author} in r/{sb}"
        url = result.get("url")
        filename = f"{_id}.{url.split('.')[-1]}"
        break
    return caption, url, filename, nsfw


async def getmeme(event, args, client, edit=False, user=None):
    """
    Fetches a random meme from reddit
    Uses meme-api.com

    Arguments:
    subreddit - custom subreddit
    """
    mem_files = None
    user = user or event.from_user.id
    if not user_is_privileged(user):
        if not chat_is_allowed(event):
            return
        if not user_is_allowed(user):
            return
    link = "https://meme-api.com/gimme"
    try:
        ref_button = InlineKeyboardButton(
            text="Refresh", callback_data=f"refmeme {user}{'_'+args if args else str()}"
        )
        reply_markup = InlineKeyboardMarkup([[ref_button]])
        if args:
            link += f"/{args}" if not args.isdigit() else str()
        caption, url, filename, nsfw = await gen_meme(
            link, (event.chat.type.value == "private")
        )
        if not url:
            if nsfw:
                return await event.reply("**NSFW is blocked!**")
            return await event.reply("**Request Failed!**")
        if url.endswith(".gif"):
            mem_files = await download_media_to_memory(url)
        if not edit:
            if mem_files:
                return await event.reply_video(
                    caption=caption,
                    video=mem_files[0],
                    has_spoiler=nsfw,
                    reply_markup=reply_markup,
                )
            return await event.reply_photo(
                caption=caption, photo=url, has_spoiler=nsfw, reply_markup=reply_markup
            )
        if mem_files:
            media = InputMediaVideo(
                media=mem_files[0], caption=caption, has_spoiler=nsfw
            )
        else:
            media = InputMediaPhoto(media=url, caption=caption, has_spoiler=nsfw)
        return await event.edit_media(media, reply_markup=reply_markup)
        # time.sleep(3)
    except pyro_errors.BadRequest as e:
        if e.ID == "MEDIA_EMPTY":
            return await getmeme(event, args, client, edit, user)
        await logger(Exception)
        return await event.reply(f"**Error:**\n`{e}`")
    except Exception as e:
        await logger(Exception)
        return await event.reply(f"**Error:**\n`{e}`")


async def refmeme(client, query):
    try:
        data, info = query.data.split(maxsplit=1)
        usearg = info.split("_", maxsplit=1)
        user, args = usearg if len(usearg) == 2 else (usearg[0], None)
        if not query.from_user.id == int(user):
            return await query.answer(
                "You're not allowed to do this!", show_alert=False
            )
        await query.answer("Refreshing…", show_alert=False)
        return await getmeme(query.message, args, None, True, user)
    except Exception:
        await logger(Exception)


async def hello(event, args, client):
    try:
        await event.reply("Hi!")
    except Exception:
        await logger(Exception)


async def up(event, args, client):
    """ping bot!"""
    user = event.from_user.id
    if not user_is_privileged(user):
        if not chat_is_allowed(event):
            return
        if not user_is_allowed(user):
            return
    ist = dt.now()
    msg = await event.reply("…")
    st = dt.now()
    ims = (st - ist).microseconds / 1000
    msg1 = "**Pong! ——** `{}`__ms__"
    st = dt.now()
    await msg.edit(msg1.format(ims))
    ed = dt.now()
    ms = (ed - st).microseconds / 1000
    await msg.edit(f"1. {msg1.format(ims)}\n2. {msg1.format(ms)}")


bot.client.add_handler(CallbackQueryHandler(refmeme, filters=regex("^refmeme")))
