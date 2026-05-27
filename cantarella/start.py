# Developed by: LastPerson07 × cantarella
# Telegram: @cantarellabots | @THEUPDATEDGUYS
import os
import asyncio
import random
import time
import shutil
import pyrogram
import requests
import hashlib
from pyrogram import Client, filters, enums
from pyrogram.errors import (
    FloodWait, UserIsBlocked, InputUserDeactivated, UserAlreadyParticipant,
    InviteHashExpired, UsernameNotOccupied, AuthKeyUnregistered, UserDeactivated, UserDeactivatedBan
)
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery, InputMediaPhoto
from config import API_ID, API_HASH, ERROR_MESSAGE, ADMINS
from database.db import db
import math
from logger import LOGGER

# --- Import additional features from additional.py ---
from cantarella.additional import (
    clean_filename,
    apply_prefix_suffix,
    smart_sleep,
    download_thumbnail,
    add_metadata_with_ffmpeg,
    PERMANENT_THUMBNAIL_URL,
    CUSTOM_SLEEP,
)

logger = LOGGER(__name__)
SUBSCRIPTION = os.environ.get('SUBSCRIPTION', 'https://graph.org/file/242b7f1b52743938d81f1.jpg')
FREE_LIMIT_SIZE = 2 * 1024 * 1024 * 1024
FREE_LIMIT_DAILY = 10
UPI_ID = os.environ.get("UPI_ID", "your_upi@oksbi")
QR_CODE = os.environ.get("QR_CODE", "https://graph.org/file/242b7f1b52743938d81f1.jpg")
REACTIONS = [
    "👍", "❤️", "🔥", "🥰", "👏", "😁", "🤔", "🤯", "😱", "🤬",
    "😢", "🎉", "🤩", "🤮", "💩", "🙏", "👌", "🕊", "🤡", "🥱",
    "🥴", "😍", "🐳", "❤️‍🔥", "🌚", "🌭", "💯", "🤣", "⚡", "🍌",
    "🏆", "💔", "🤨", "😐", "🍓", "🍾", "💋", "🖕", "😈", "😴",
    "😭", "🤓", "👻", "👨‍💻", "👀", "🎃", "🙈", "😇", "😨", "🤝",
    "✍", "🤗", "🫡", "🎅", "🎄", "☃", "💅", "🤪", "🗿", "🆒",
    "💘", "🙉", "🦄", "😘", "💊", "🙊", "😎", "👾", "🤷‍♂️", "🤷‍♀️",
    "😡"
]

dev_text = "👨‍💻 Mind Behind This Bot:\n• @DmOwner\n• @akaza7902"
expected_dev_hash = "b9e63b7578bdec13f3cb3162fe5f5e93dccaba3bfd5c8ddacbb90ffdcdcce402"
channels_text = "📢 Official Channels:\n• @ReX_update\n• @THEUPDATEDGUYS\n\nStay updated for new features!"
expected_channels_hash = "e19212e571bd0f6626450dd790029d392c0748c554d4b386a0c0752f4148d37d"

if (
    hashlib.sha256(dev_text.encode('utf-8')).hexdigest() != expected_dev_hash or
    hashlib.sha256(channels_text.encode('utf-8')).hexdigest() != expected_channels_hash
):
    raise Exception("Tampered developer info detected! Bot will not start. Fuck the code - crashing now.")


# ===========================================================================
# Custom exception for cancellation (ported from Code 1)
# ===========================================================================

class ProcessCancelled(Exception):
    """Raised when the user cancels an ongoing task."""
    pass


# ===========================================================================
# Task registry — supports both private chats and groups
# Each active task is keyed by "user_id:chat_id" so multiple users in
# different groups can run independently (same approach as Code 1).
# ===========================================================================

class batch_temp(object):
    IS_BATCH      = {}   # True  → no active task (slot is free)
                         # False → task is running
    CANCEL_TASKS  = {}   # True  → cancellation requested
    DOWNLOAD_TASKS = {}  # asyncio.Task references for in-flight downloads
    ACTIVE_SESSIONS = {} # reusable pyrogram Client objects per user


def get_task_key(user_id: int, chat_id: int) -> str:
    """
    Build a unique task key for (user, chat) pair.
    • Private chat  → user_id == chat_id  → "uid:uid"  (backward-compat)
    • Group / super → different ids        → "uid:cid"
    """
    return f"{user_id}:{chat_id}"


# ===========================================================================
# Script strings
# ===========================================================================

class script(object):

    START_TXT = """<b>👋 Hello {},</b>
<b>🤖 I am <a href=https://t.me/{}>{}</a></b>
<i>Your Professional Restricted Content Saver Bot.</i>
<blockquote><b>🚀 System Status: 🟢 Online</b>
<b>⚡ Performance: 10x High-Speed Processing</b>
<b>🔐 Security: End-to-End Encrypted</b>
<b>📊 Uptime: 99.9% Guaranteed</b></blockquote>
<b>👇 Select an Option Below to Get Started:</b>
"""
    HELP_TXT = """<b>📚 Comprehensive Help & User Guide</b>
<blockquote><b>1️⃣ Public Channels (No Login Required)</b></blockquote>
• Forward or send the post link directly.
• Compatible with any public channel or group.
• <i>Example Link:</i> <code>https://t.me/channel/123</code>
<blockquote><b>2️⃣ Private/Restricted Channels (Login Required)</b></blockquote>
• Use <code>/login</code> to securely connect your Telegram account.
• Send the private link (e.g., <code>t.me/c/123...</code>).
• Bot accesses content using your authenticated session.
<blockquote><b>3️⃣ Batch Downloading Mode</b></blockquote>
• Initiate with <code>/batch</code> for multiple files.
• Follow interactive prompts for seamless processing.
<blockquote><b>🛑 Free User Limitations:</b></blockquote>
• <b>Daily Quota:</b> 10 Files / 24 Hours
• <b>File Size Cap:</b> 2GB Maximum
<blockquote><b>💎 Premium Membership Benefits:</b></blockquote>
• Unlimited Downloads & No Restrictions.
• Priority Support & Advanced Features.
<blockquote><b>🕐 Batch Sleep Settings:</b></blockquote>
• Use <code>/setsleep 3 5 7 10</code> to set custom delay between downloads.
• Use <code>/getsleep</code> to view your current sleep settings.
<blockquote><b>👥 Group Support:</b></blockquote>
• Send a Telegram link directly in any group where the bot is a member.
• <code>/cancel</code> and <code>/setsleep</code> work in groups too!
"""
    ABOUT_TXT = """<b>ℹ️ About This Bot</b>
<blockquote><b>╭────[ 🧩 Technical Stack ]────⍟</b>
<b>├⍟ 🤖 Bot Name : <a href=http://t.me/THEUPDATEDGUYS_Bot>Save Content</a></b>
<b>├⍟ 👨‍💻 Developer : <a href=https://t.me/DmOwner>Ⓜ️ark X cantarella</a></b>
<b>├⍟ 📚 Library : <a href='https://docs.pyrogram.org/'>Pyrogram Async</a></b>
<b>├⍟ 🐍 Language : <a href='https://www.python.org/'>Python 3.11+</a></b>
<b>├⍟ 🗄 Database : <a href='https://www.mongodb.com/'>MongoDB Atlas Cluster</a></b>
<b>├⍟ 📡 Hosting : Dedicated High-Speed VPS</b>
<b>╰───────────────⍟</b></blockquote>
"""
    PREMIUM_TEXT = """<b>💎 Premium Membership Plans</b>
<b>Unlock Unlimited Access & Advanced Features!</b>
<blockquote><b>✨ Key Benefits:</b>
<b>♾️ Unlimited Daily Downloads</b>
<b>📂 Support for 4GB+ File Sizes</b>
<b>⚡ Instant Processing (Zero Delay)</b>
<b>🖼 Customizable Thumbnails</b>
<b>📝 Personalized Captions</b>
<b>🛂 24/7 Priority Support</b></blockquote>
<blockquote><b>💳 Pricing Options:</b></blockquote>
• <b>1 Month Plan:</b> ₹50 / $1 (Billed Monthly)
• <b>3 Month Plan:</b> ₹120 / $2.5 (Save 20%)
• <b>Lifetime Access:</b> ₹200 / $4 (One-Time Payment)
<blockquote><b>👇 Secure Payment:</b></blockquote>
<b>💸 UPI ID:</b> <code>{}</code>
<b>📸 QR Code:</b> <a href='{}'>Scan to Pay</a>
<i>After Payment: Send Screenshot to Admin for Instant Activation.</i>
"""
    CAPTION = """<b><a href="https://t.me/THEUPDATEDGUYS"></a></b>\n\n<b>⚜️ Powered By : <a href="https://t.me/THEUPDATEDGUYS">THE UPDATED GUYS 😎</a></b>"""
    LIMIT_REACHED = """<b>🚫 Daily Limit Exceeded</b>
<b>Your 10 free saves for today have been used.</b>
<i>Quota resets automatically after 24 hours from first download.</i>
<blockquote><b>🔓 Upgrade to Premium for Unlimited Access!</b></blockquote>
Remove all restrictions and enjoy seamless downloading.
"""
    SIZE_LIMIT = """<b>⚠️ File Size Exceeded</b>
<b>Free tier limited to 2GB per file.</b>
<blockquote><b>🔓 Upgrade to Premium</b></blockquote>
Download files up to 4GB and beyond with no limits!
"""


# ===========================================================================
# Helpers
# ===========================================================================

def humanbytes(size):
    if not size:
        return "0B"
    power = 2 ** 10
    n = 0
    Dic_powerN = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'


def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
          ((str(hours) + "h, ") if hours else "") + \
          ((str(minutes) + "m, ") if minutes else "") + \
          ((str(seconds) + "s, ") if seconds else "")
    return tmp[:-2] if tmp else "0s"


def get_message_type(msg):
    if getattr(msg, 'document', None):  return "Document"
    if getattr(msg, 'video', None):     return "Video"
    if getattr(msg, 'photo', None):     return "Photo"
    if getattr(msg, 'audio', None):     return "Audio"
    if getattr(msg, 'text', None):      return "Text"
    return None


def make_progress_bar(percentage: float) -> str:
    """
    Builds a progress bar like: [■■■■■■▨□□□□□]
    Total 12 slots. Filled = ■, partial tip = ▨, empty = □
    """
    total_slots = 12
    filled = int(percentage / 100 * total_slots)
    partial = 1 if filled < total_slots and percentage > 0 else 0
    empty = total_slots - filled - partial
    return "[" + "■" * filled + ("▨" if partial else "") + "□" * empty + "]"


# ===========================================================================
# Progress callback — async, inline edits the status message directly.
# Attaches a 🛑 Cancel inline button carrying the task_key so it works in
# both private chats and groups.
# ===========================================================================

UPDATE_DELAY = 5   # seconds between progress message edits

async def progress_callback(current, total, smsg, mode, start_time, task_key, file_name="", user_name=""):
    """
    Async progress callback compatible with pyrogram's download_media /
    send_* progress_args.

    Parameters
    ----------
    current   : bytes transferred so far
    total     : total bytes
    smsg      : the status Message object to edit in-place
    mode      : "download" | "upload"
    start_time: time.time() when the transfer started
    task_key  : "user_id:chat_id" string for cancel checks
    file_name : display name for the file
    user_name : first name of the user who triggered the task
    """
    if smsg is None:
        return

    # Fast-path cancel check (no await needed)
    if batch_temp.CANCEL_TASKS.get(task_key, False):
        raise ProcessCancelled("Cancelled by user")

    now = time.time()
    cache_attr = f"_last_edit_{smsg.id}"
    last_edit = getattr(progress_callback, cache_attr, 0)
    if now - last_edit < UPDATE_DELAY and current != total:
        return
    setattr(progress_callback, cache_attr, now)

    diff = now - start_time
    percentage = (current / total * 100) if total else 0
    speed = current / diff if diff > 0 else 0
    eta_secs = (total - current) / speed if speed > 0 else 0

    bar = make_progress_bar(percentage)

    elapsed_str = TimeFormatter(int(diff * 1000))
    eta_str = f"{int(eta_secs)}s" if eta_secs > 0 else "-"

    display_name = file_name if file_name else "File"
    status_label = "Download" if mode == "download" else "Upload"

    # Use provided user_name; fall back to user_id from task_key
    display_user = user_name if user_name else task_key.split(':')[0]

    text = (
        f"<blockquote><b>{display_name}</b></blockquote>\n"
        f"<blockquote><b>{bar} {percentage:.1f}%</b></blockquote>\n"
        f"<blockquote><b>Processed: {humanbytes(current)} of {humanbytes(total)}</b></blockquote>\n"
        f"<blockquote><b>Status: {status_label} | ETA: {eta_str}</b></blockquote>\n"
        f"<blockquote><b>Speed: {humanbytes(speed)}/s | Elapsed: {elapsed_str}</b></blockquote>\n"
        f"<blockquote><b>Engine: {'Aria2 v1.36.0' if mode == 'download' else 'PyroMulti v2.2.11'}</b></blockquote>\n"
        f"<blockquote><b>Mode:  #Leech | #{'Aria2' if mode == 'download' else 'TG'}</b></blockquote>\n"
        f"<blockquote><b>User: {display_user} | ID: {task_key.split(':')[0]}</b></blockquote>"
    )

    cancel_markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("🛑 Cancel", callback_data=f"cancel_{task_key}")
    ]])

    try:
        await smsg.edit_text(text, reply_markup=cancel_markup, parse_mode=enums.ParseMode.HTML)
    except Exception:
        pass


# ===========================================================================
# Cancel callback — handles both "cancel_uid" and "cancel_uid:cid" formats
# ===========================================================================

@Client.on_callback_query(filters.regex(r"^cancel_"))
async def cancel_callback(client: Client, callback_query: CallbackQuery):
    data     = callback_query.data          # "cancel_<payload>"
    payload  = data[len("cancel_"):]        # "<user_id>" or "<user_id>:<chat_id>"

    if ":" in payload:
        user_id  = int(payload.split(":", 1)[0])
        task_key = payload
    else:
        user_id  = int(payload)
        task_key = payload

    # Only the owner of the task may cancel it
    if callback_query.from_user.id != user_id:
        await callback_query.answer("⚠️ This is not your process!", show_alert=True)
        return

    batch_temp.CANCEL_TASKS[task_key] = True
    batch_temp.IS_BATCH[task_key]     = True   # mark slot as free so next task can start

    # Cancel in-flight download asyncio.Task if registered
    task = batch_temp.DOWNLOAD_TASKS.get(task_key)
    if task and not task.done():
        task.cancel()

    await callback_query.answer("🛑 Cancelling…", show_alert=True)
    try:
        await callback_query.message.edit_text(
            "<b>🛑 Cancellation In Progress</b>\n\n"
            "⚠️ Stopping current operation…\n"
            "⚠️ Cleaning up temporary files…",
            parse_mode=enums.ParseMode.HTML
        )
    except Exception:
        pass


# ===========================================================================
# /start  — private + group
# ===========================================================================

@Client.on_message(filters.command(["start"]) & filters.user(ADMINS))
async def send_start(client: Client, message: Message):
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
    try:
        await message.react(emoji=random.choice(REACTIONS), big=True)
    except Exception:
        pass

    apis = ["https://api.waifu.pics/sfw/waifu", "https://nekos.life/api/v2/img/waifu"]
    try:
        response = requests.get(random.choice(apis))
        response.raise_for_status()
        photo_url = response.json()["url"]
    except Exception as e:
        logger.error(f"Failed to fetch image from API: {e}")
        photo_url = "https://i.postimg.cc/kX9tjGXP/16.png"

    buttons = [
        [
            InlineKeyboardButton("💎 Buy Premium", callback_data="buy_premium"),
            InlineKeyboardButton("🆘 Help & Guide", callback_data="help_btn")
        ],
        [
            InlineKeyboardButton("⚙️ Settings Panel", callback_data="settings_btn"),
            InlineKeyboardButton("ℹ️ About Bot", callback_data="about_btn")
        ],
        [
            InlineKeyboardButton('📢 Channels', callback_data="channels_info"),
            InlineKeyboardButton('👨‍💻 Developers', callback_data="dev_info")
        ]
    ]
    bot = await client.get_me()
    await client.send_photo(
        chat_id=message.chat.id,
        photo=photo_url,
        caption=script.START_TXT.format(message.from_user.mention, bot.username, bot.first_name),
        reply_markup=InlineKeyboardMarkup(buttons),
        reply_to_message_id=message.id,
        parse_mode=enums.ParseMode.HTML
    )


# ===========================================================================
# /help  — private + group
# ===========================================================================

@Client.on_message(filters.command(["help"]) & (filters.private | filters.group))
async def send_help(client: Client, message: Message):
    buttons = [[InlineKeyboardButton("❌ Close Menu", callback_data="close_btn")]]
    await client.send_message(
        chat_id=message.chat.id,
        text=script.HELP_TXT,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=enums.ParseMode.HTML
    )


# ===========================================================================
# /plan  — private + group
# ===========================================================================

@Client.on_message(filters.command(["plan", "myplan", "premium"]) & (filters.private | filters.group))
async def send_plan(client: Client, message: Message):
    buttons = [
        [InlineKeyboardButton("📸 Send Payment Proof", url="https://t.me/DmOwner")],
        [InlineKeyboardButton("❌ Close Menu", callback_data="close_btn")]
    ]
    await client.send_photo(
        chat_id=message.chat.id,
        photo=SUBSCRIPTION,
        caption=script.PREMIUM_TEXT.format(UPI_ID, QR_CODE),
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=enums.ParseMode.HTML
    )


# ===========================================================================
# /cancel  — private + group  (ported from Code 1)
# ===========================================================================

@Client.on_message(filters.command(["cancel"]) & (filters.private | filters.group))
async def send_cancel(client: Client, message: Message):
    user_id  = message.from_user.id
    chat_id  = message.chat.id
    task_key = get_task_key(user_id, chat_id)

    # If no task is running for this (user, chat) slot → nothing to cancel
    if batch_temp.IS_BATCH.get(task_key, True) is True:
        await client.send_message(
            chat_id=message.chat.id,
            text="<b>❌ No Active Process To Cancel.</b>",
            reply_to_message_id=message.id,
            parse_mode=enums.ParseMode.HTML
        )
        return

    batch_temp.CANCEL_TASKS[task_key] = True
    batch_temp.IS_BATCH[task_key]     = True

    # Cancel in-flight download asyncio.Task if registered
    task = batch_temp.DOWNLOAD_TASKS.get(task_key)
    if task and not task.done():
        task.cancel()

    await client.send_message(
        chat_id=message.chat.id,
        text=(
            "<b>🛑 Cancelling All Processes Immediately!</b>\n\n"
            "⚠️ Stopping current download/upload…\n"
            "⚠️ Cleaning up temporary files…"
        ),
        reply_to_message_id=message.id,
        parse_mode=enums.ParseMode.HTML
    )


# ===========================================================================
# /setsleep  — private + group
# ===========================================================================

@Client.on_message(filters.command(["setsleep"]) & (filters.private | filters.group))
async def set_sleep(client: Client, message: Message):
    try:
        parts = message.text.split()[1:]
        if not parts:
            await message.reply(
                "**Usage:** `/setsleep 3 5 7 10`\n\n"
                "Provide space-separated sleep values in seconds.\n"
                "Bot will randomly pick one value for each download to avoid detection.\n\n"
                "**Allowed range:** 1-1000 seconds\n"
                "**Example:** `/setsleep 3 5 7 10 12 15`"
            )
            return

        sleep_values = [int(x) for x in parts if x.isdigit() and 1 <= int(x) <= 1000]
        if not sleep_values:
            await message.reply("❌ Please provide valid sleep values between 1-1000 seconds!")
            return

        CUSTOM_SLEEP[message.from_user.id] = sleep_values
        await message.reply(
            f"✅ **Sleep values set successfully!**\n\n"
            f"Values: `{', '.join(map(str, sleep_values))}` seconds\n"
            f"Bot will randomly pick one value between downloads.\n\n"
            f"💡 **Tip:** More varied values = better anti-detection!"
        )
    except ValueError:
        await message.reply("❌ Please provide valid numeric values only!")


# ===========================================================================
# /getsleep  — private + group
# ===========================================================================

@Client.on_message(filters.command(["getsleep"]) & (filters.private | filters.group))
async def get_sleep(client: Client, message: Message):
    sleep_values = CUSTOM_SLEEP.get(message.from_user.id, [3, 5, 7, 10])
    await message.reply(
        f"**⏱️ Current Sleep Settings:**\n\n"
        f"Values: `{', '.join(map(str, sleep_values))}` seconds\n"
        f"Random selection with ±20% jitter for natural behavior.\n\n"
        f"Use `/setsleep` to change these values."
    )


# ===========================================================================
# Settings panel helper
# ===========================================================================

async def settings_panel(client, callback_query):
    user_id    = callback_query.from_user.id
    is_premium = await db.check_premium(user_id)
    badge      = "💎 Premium Member" if is_premium else "👤 Standard User"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📜 Command List",       callback_data="cmd_list_btn")],
        [InlineKeyboardButton("📊 Usage Stats",        callback_data="user_stats_btn")],
        [InlineKeyboardButton("🗑 Dump Chat Settings", callback_data="dump_chat_btn")],
        [InlineKeyboardButton("🖼 Manage Thumbnail",   callback_data="thumb_btn")],
        [InlineKeyboardButton("📝 Edit Caption",       callback_data="caption_btn")],
        [InlineKeyboardButton("⬅️ Return to Home",     callback_data="start_btn")]
    ])
    text = (
        f"<b>⚙️ Settings Dashboard</b>\n\n"
        f"<b>Account Status:</b> {badge}\n"
        f"<b>User ID:</b> <code>{user_id}</code>\n\n"
        f"<i>Customize and manage your bot preferences below for an optimized experience:</i>"
    )
    await callback_query.edit_message_caption(
        caption=text,
        reply_markup=buttons,
        parse_mode=enums.ParseMode.HTML
    )


# ===========================================================================
# Main save handler — private + group
# ===========================================================================

@Client.on_message(filters.text & (filters.private | filters.group) & ~filters.regex("^/"))
async def save(client: Client, message: Message):
    if "https://t.me/" not in message.text:
        return

    user_id   = message.from_user.id
    chat_id   = message.chat.id
    task_key  = get_task_key(user_id, chat_id)
    user_name = message.from_user.first_name or str(user_id)

    # Limit check (skip in groups — limits are per-user in private chats)
    if filters.private(None, message):
        is_limit_reached = await db.check_limit(user_id)
        if is_limit_reached:
            btn = InlineKeyboardMarkup([[InlineKeyboardButton("💎 Upgrade to Premium", callback_data="buy_premium")]])
            return await message.reply_photo(
                photo=SUBSCRIPTION,
                caption=script.LIMIT_REACHED,
                reply_markup=btn,
                parse_mode=enums.ParseMode.HTML
            )

    # Already processing?
    if batch_temp.IS_BATCH.get(task_key, True) is False:
        return await message.reply_text(
            "<b>⚠️ A Task is Currently Processing.</b>\n"
            "<i>Please wait for completion or use /cancel to stop.</i>",
            parse_mode=enums.ParseMode.HTML
        )

    datas = message.text.split("/")
    temp  = datas[-1].replace("?single", "").split("-")
    fromID = int(temp[0].strip())
    try:
        toID = int(temp[1].strip())
    except Exception:
        toID = fromID

    # Mark slot as busy
    batch_temp.IS_BATCH[task_key]     = False
    batch_temp.CANCEL_TASKS[task_key] = False

    total_items = toID - fromID + 1
    completed   = 0

    is_private_link = "https://t.me/c/" in message.text
    is_batch_link   = "https://t.me/b/" in message.text
    is_public_link  = not is_private_link and not is_batch_link

    try:
        for msgid in range(fromID, toID + 1):

            # ── Cancel check at top of every iteration ──────────────────
            if batch_temp.CANCEL_TASKS.get(task_key, False):
                await client.send_message(
                    chat_id=message.chat.id,
                    text=(
                        f"<b>🛑 Batch Process Cancelled!</b>\n\n"
                        f"✅ Completed: {completed}/{total_items} items\n"
                        f"❌ Cancelled at message {msgid}/{toID}"
                    ),
                    reply_to_message_id=message.id,
                    parse_mode=enums.ParseMode.HTML
                )
                break

            if is_public_link:
                username = datas[3]
                try:
                    await client.copy_message(
                        chat_id=message.chat.id,
                        from_chat_id=username,
                        message_id=msgid,
                        reply_to_message_id=message.id
                    )
                    await db.add_traffic(user_id)
                    completed += 1
                except Exception:
                    pass
            else:
                # Private / restricted content needs a user session
                user_data = await db.get_session(user_id)
                if user_data is None:
                    await message.reply(
                        "<b>🔒 Authentication Required</b>\n\n"
                        "<i>Use /login to securely authorize your account.</i>",
                        parse_mode=enums.ParseMode.HTML
                    )
                    batch_temp.IS_BATCH[task_key] = True
                    return

                try:
                    acc = Client(
                        "saverestricted",
                        session_string=user_data,
                        api_hash=API_HASH,
                        api_id=API_ID,
                        in_memory=True,
                        max_concurrent_transmissions=10
                    )
                    await acc.connect()
                except Exception as e:
                    batch_temp.IS_BATCH[task_key] = True
                    return await message.reply(
                        f"<b>❌ Authentication Failed</b>\n\n"
                        f"<i>Your session may have expired. Please /logout and /login again.</i>\n"
                        f"<code>{e}</code>",
                        parse_mode=enums.ParseMode.HTML
                    )

                if is_private_link:
                    chat_target = int("-100" + datas[4])
                elif is_batch_link:
                    chat_target = datas[4]
                else:
                    chat_target = datas[3]

                try:
                    success = await handle_restricted_content(
                        client, acc, message, chat_target, msgid, task_key, user_name
                    )
                    if success:
                        completed += 1
                except ProcessCancelled:
                    await client.send_message(
                        chat_id=message.chat.id,
                        text=(
                            f"<b>🛑 Batch Process Cancelled!</b>\n\n"
                            f"✅ Completed: {completed}/{total_items} items"
                        ),
                        reply_to_message_id=message.id,
                        parse_mode=enums.ParseMode.HTML
                    )
                    break
                except Exception as e:
                    if ERROR_MESSAGE:
                        await client.send_message(
                            message.chat.id,
                            f"Error: {e}",
                            reply_to_message_id=message.id
                        )

            # ── Cancel check before sleep ────────────────────────────────
            if batch_temp.CANCEL_TASKS.get(task_key, False):
                break

            if msgid < toID:
                try:
                    await smart_sleep(user_id)
                except Exception:
                    pass

            # Progress milestone every 5 files
            if completed > 0 and completed % 5 == 0 and completed < total_items:
                try:
                    await client.send_message(
                        message.chat.id,
                        f"📊 Progress: {completed}/{total_items} completed…",
                        reply_to_message_id=message.id
                    )
                except Exception:
                    pass

    except ProcessCancelled:
        pass
    except Exception as e:
        logger.error(f"Error in batch process: {e}")
    finally:
        batch_temp.IS_BATCH[task_key]     = True
        batch_temp.CANCEL_TASKS[task_key] = False
        batch_temp.DOWNLOAD_TASKS.pop(task_key, None)

        if completed > 0 and not batch_temp.CANCEL_TASKS.get(task_key, False):
            try:
                await client.send_message(
                    message.chat.id,
                    f"✅ <b>Batch Complete!</b>\n\nProcessed: {completed}/{total_items} items",
                    reply_to_message_id=message.id,
                    parse_mode=enums.ParseMode.HTML
                )
            except Exception:
                pass


# ===========================================================================
# handle_restricted_content
# — Downloads, renames, adds metadata, then uploads.
# — Uses async progress_callback with inline Cancel button.
# — After download: edits status to "Adding Metadata…" before metadata step.
# — After metadata:  edits status to "Uploading…" before upload step.
# ===========================================================================

async def handle_restricted_content(
    client: Client,
    acc,
    message: Message,
    chat_target,
    msgid: int,
    task_key: str,
    user_name: str = ""
) -> bool:
    """
    Returns True on successful upload, False on skip/error.
    Raises ProcessCancelled if the user cancels mid-way.
    """
    user_id = message.from_user.id

    # Resolve display name for the user (first name takes priority)
    display_user = user_name if user_name else (message.from_user.first_name or str(user_id))

    # ── Fetch source message ─────────────────────────────────────────────
    try:
        msg: Message = await acc.get_messages(chat_target, msgid)
    except Exception as e:
        logger.error(f"Error fetching message {msgid}: {e}")
        return False

    if msg.empty:
        return False

    msg_type = get_message_type(msg)
    if not msg_type:
        return False

    # ── File-size gate (free users) ──────────────────────────────────────
    file_size = 0
    if msg_type == "Document": file_size = getattr(msg.document, 'file_size', 0)
    elif msg_type == "Video":  file_size = getattr(msg.video,    'file_size', 0)
    elif msg_type == "Audio":  file_size = getattr(msg.audio,    'file_size', 0)

    if file_size > FREE_LIMIT_SIZE:
        if not await db.check_premium(user_id):
            btn = InlineKeyboardMarkup([[
                InlineKeyboardButton("💎 Upgrade to Premium", callback_data="buy_premium")
            ]])
            await client.send_message(
                message.chat.id,
                script.SIZE_LIMIT,
                reply_markup=btn,
                parse_mode=enums.ParseMode.HTML
            )
            return False

    # ── Text messages ────────────────────────────────────────────────────
    if msg_type == "Text":
        try:
            await client.send_message(
                message.chat.id, msg.text,
                entities=msg.entities,
                parse_mode=enums.ParseMode.HTML
            )
            return True
        except Exception:
            return False

    # ── Pre-download cancel check ────────────────────────────────────────
    if batch_temp.CANCEL_TASKS.get(task_key, False):
        raise ProcessCancelled("Cancelled before download")

    await db.add_traffic(user_id)

    # ── Resolve display filename early for UI ────────────────────────────
    display_name = "File"
    if msg_type == "Document" and msg.document:
        display_name = msg.document.file_name or "Document"
    elif msg_type == "Video" and msg.video:
        display_name = msg.video.file_name or "Video"
    elif msg_type == "Audio" and msg.audio:
        display_name = msg.audio.file_name or "Audio"

    cancel_markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("🛑 Cancel", callback_data=f"cancel_{task_key}")
    ]])

    smsg = await client.send_message(
        message.chat.id,
        f"<blockquote><b>{display_name}</b></blockquote>\n"
        f"<blockquote><b>[□□□□□□□□□□□□] 0.0%</b></blockquote>\n"
        f"<blockquote><b>Processed: 0 B of {humanbytes(file_size)}</b></blockquote>\n"
        f"<blockquote><b>Status: Download | ETA: -</b></blockquote>\n"
        f"<blockquote><b>Speed: 0.0 B/s | Elapsed: 0s</b></blockquote>\n"
        f"<blockquote><b>Engine: Aria2 v1.36.0</b></blockquote>\n"
        f"<blockquote><b>Mode:  #Leech | #Aria2</b></blockquote>\n"
        f"<blockquote><b>User: {display_user} | ID: {user_id}</b></blockquote>",
        reply_to_message_id=message.id,
        reply_markup=cancel_markup,
        parse_mode=enums.ParseMode.HTML
    )

    temp_dir = f"downloads/{message.chat.id}_{message.id}_{msgid}"
    os.makedirs(temp_dir, exist_ok=True)

    file       = None
    start_time = time.time()

    # ── DOWNLOAD ─────────────────────────────────────────────────────────
    try:
        dl_task = asyncio.create_task(
            acc.download_media(
                msg,
                file_name=f"{temp_dir}/",
                progress=progress_callback,
                progress_args=(smsg, "download", start_time, task_key, display_name, display_user)
            )
        )
        batch_temp.DOWNLOAD_TASKS[task_key] = dl_task

        try:
            file = await dl_task
        except asyncio.CancelledError:
            raise ProcessCancelled("Download task cancelled")
        finally:
            batch_temp.DOWNLOAD_TASKS.pop(task_key, None)

    except ProcessCancelled:
        if file and os.path.exists(file):
            try: os.remove(file)
            except Exception: pass
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        try: await smsg.delete()
        except Exception: pass
        raise

    except Exception as e:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        if "Cancelled" in str(e):
            try: await smsg.edit("<b>❌ Task Cancelled</b>", parse_mode=enums.ParseMode.HTML)
            except Exception: pass
            raise ProcessCancelled(str(e))
        try: await smsg.delete()
        except Exception: pass
        return False

    # ── POST-DOWNLOAD cancel check ───────────────────────────────────────
    if batch_temp.CANCEL_TASKS.get(task_key, False):
        if file and os.path.exists(file):
            try: os.remove(file)
            except Exception: pass
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        try: await smsg.delete()
        except Exception: pass
        raise ProcessCancelled("Cancelled after download")

    # ── Filename cleanup ─────────────────────────────────────────────────
    if file and os.path.exists(file):
        old_filename   = os.path.basename(file)
        dir_name       = os.path.dirname(file)
        cleaned        = clean_filename(old_filename)
        final_filename = apply_prefix_suffix(cleaned)

        if old_filename != final_filename:
            new_path = os.path.join(dir_name, final_filename)
            os.rename(file, new_path)
            file = new_path
    else:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        try: await smsg.delete()
        except Exception: pass
        return False

    # ── Resolve actual file size after download ──────────────────────────
    actual_size = os.path.getsize(file) if file and os.path.exists(file) else file_size
    size_str = humanbytes(actual_size)

    # ── METADATA — edit progress message to show Metadata UI ─────────────
    try:
        await smsg.edit_text(
            f"<blockquote><b>{final_filename}</b></blockquote>\n"
            f"<blockquote><b>Status: Metadata</b></blockquote>\n"
            f"<blockquote><b>Size: {size_str}</b></blockquote>\n"
            f"<blockquote><b>Engine: ffmpeg v4.4.2-0</b></blockquote>\n"
            f"<blockquote><b>User: {display_user} | ID: {user_id}</b></blockquote>",
            reply_markup=cancel_markup,
            parse_mode=enums.ParseMode.HTML
        )
    except Exception:
        pass

    if batch_temp.CANCEL_TASKS.get(task_key, False):
        if file and os.path.exists(file):
            try: os.remove(file)
            except Exception: pass
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        try: await smsg.delete()
        except Exception: pass
        raise ProcessCancelled("Cancelled before metadata")

    file, _ = await add_metadata_with_ffmpeg(file, final_filename)

    # ── POST-METADATA cancel check ───────────────────────────────────────
    if batch_temp.CANCEL_TASKS.get(task_key, False):
        if file and os.path.exists(file):
            try: os.remove(file)
            except Exception: pass
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        try: await smsg.delete()
        except Exception: pass
        raise ProcessCancelled("Cancelled after metadata")

    # ── Edit progress message → Upload starting UI ────────────────────────
    try:
        await smsg.edit_text(
            f"<b>{final_filename}</b></blockquote>\n"
            f"<blockquote><b>[□□□□□□□□□□□□] 0.0%</b></blockquote>\n"
            f"<blockquote><b>Processed: 0 B of {size_str}</b></blockquote>\n"
            f"<blockquote><b>Status: Upload | ETA: -</b></blockquote>\n"
            f"<blockquote><b>Speed: 0.0 B/s | Elapsed: 0s</b></blockquote>\n"
            f"<blockquote><b>Engine: PyroMulti v2.2.11</b></blockquote>\n"
            f"<blockquote><b>Mode:  #Leech | #Aria2</b></blockquote>\n"
            f"<blockquote><b>User: {display_user} | ID: {user_id}</b></blockquote>",
            reply_markup=cancel_markup,
            parse_mode=enums.ParseMode.HTML
        )
    except Exception:
        pass

    # ── Thumbnail resolution (priority: permanent > DB > original) ───────
    ph_path = None

    if PERMANENT_THUMBNAIL_URL:
        ph_path = await download_thumbnail(PERMANENT_THUMBNAIL_URL)

    if not ph_path:
        thumb_id = await db.get_thumbnail(user_id)
        if thumb_id:
            try:
                ph_path = await client.download_media(
                    thumb_id, file_name=f"{temp_dir}/custom_thumb.jpg"
                )
            except Exception as e:
                logger.error(f"Failed to download custom thumb: {e}")

    if not ph_path:
        try:
            if msg_type == "Video" and msg.video.thumbs:
                ph_path = await acc.download_media(
                    msg.video.thumbs[0].file_id, file_name=f"{temp_dir}/thumb.jpg"
                )
            elif msg_type == "Document" and msg.document.thumbs:
                ph_path = await acc.download_media(
                    msg.document.thumbs[0].file_id, file_name=f"{temp_dir}/thumb.jpg"
                )
        except Exception:
            pass

    # ── Caption ──────────────────────────────────────────────────────────
    custom_caption = await db.get_caption(user_id)
    if custom_caption:
        final_caption = custom_caption.format(
            filename=os.path.basename(file),
            size=humanbytes(file_size)
        )
    else:
        final_caption = script.CAPTION
        if msg.caption:
            final_caption += f"\n\n{msg.caption}"

    # ── UPLOAD ───────────────────────────────────────────────────────────
    upload_success = False
    start_time     = time.time()

    try:
        if msg_type == "Document":
            if batch_temp.CANCEL_TASKS.get(task_key, False):
                raise ProcessCancelled("Cancelled before upload")
            await client.send_document(
                message.chat.id, file,
                thumb=ph_path, caption=final_caption,
                file_name=os.path.basename(file),
                reply_to_message_id=message.id,
                parse_mode=enums.ParseMode.HTML,
                progress=progress_callback,
                progress_args=(smsg, "upload", start_time, task_key, final_filename, display_user)
            )
            upload_success = True

        elif msg_type == "Video":
            if batch_temp.CANCEL_TASKS.get(task_key, False):
                raise ProcessCancelled("Cancelled before upload")
            await client.send_video(
                message.chat.id, file,
                duration=msg.video.duration,
                width=msg.video.width,
                height=msg.video.height,
                thumb=ph_path, caption=final_caption,
                file_name=os.path.basename(file),
                reply_to_message_id=message.id,
                parse_mode=enums.ParseMode.HTML,
                progress=progress_callback,
                progress_args=(smsg, "upload", start_time, task_key, final_filename, display_user)
            )
            upload_success = True

        elif msg_type == "Audio":
            if batch_temp.CANCEL_TASKS.get(task_key, False):
                raise ProcessCancelled("Cancelled before upload")
            await client.send_audio(
                message.chat.id, file,
                thumb=ph_path, caption=final_caption,
                file_name=os.path.basename(file),
                reply_to_message_id=message.id,
                parse_mode=enums.ParseMode.HTML,
                progress=progress_callback,
                progress_args=(smsg, "upload", start_time, task_key, final_filename, display_user)
            )
            upload_success = True

        elif msg_type == "Photo":
            if batch_temp.CANCEL_TASKS.get(task_key, False):
                raise ProcessCancelled("Cancelled before upload")
            await client.send_photo(
                message.chat.id, file,
                caption=final_caption,
                reply_to_message_id=message.id,
                parse_mode=enums.ParseMode.HTML
            )
            upload_success = True

    except ProcessCancelled:
        raise

    except Exception as e:
        if ERROR_MESSAGE:
            await client.send_message(
                message.chat.id,
                f"Upload Failed: {e}",
                reply_to_message_id=message.id
            )

    # ── Cleanup ──────────────────────────────────────────────────────────
    if file and os.path.exists(file):
        try: os.remove(file)
        except Exception: pass

    if ph_path and PERMANENT_THUMBNAIL_URL and os.path.exists(ph_path):
        try: os.remove(ph_path)
        except Exception: pass

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)

    try:
        await client.delete_messages(message.chat.id, [smsg.id])
    except Exception:
        pass

    return upload_success


# ===========================================================================
# Callback query handler
# ===========================================================================

@Client.on_callback_query()
async def button_callbacks(client: Client, callback_query: CallbackQuery):
    # cancel_ callbacks are handled by the dedicated handler above;
    # make sure we don't shadow them here.
    data    = callback_query.data
    message = callback_query.message
    if not message:
        return

    if data == "dev_info":
        await callback_query.answer(text=dev_text, show_alert=True)

    elif data == "channels_info":
        await callback_query.answer(text=channels_text, show_alert=True)

    elif data == "settings_btn":
        await settings_panel(client, callback_query)

    elif data == "buy_premium":
        buttons = [
            [InlineKeyboardButton("📸 Send Payment Proof", url="https://t.me/DmOwner")],
            [InlineKeyboardButton("⬅️ Back to Home", callback_data="start_btn")]
        ]
        await client.edit_message_media(
            chat_id=message.chat.id,
            message_id=message.id,
            media=InputMediaPhoto(
                media=SUBSCRIPTION,
                caption=script.PREMIUM_TEXT.format(
                    callback_query.from_user.mention, UPI_ID, QR_CODE
                )
            ),
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data == "help_btn":
        buttons = [[InlineKeyboardButton("⬅️ Back to Home", callback_data="start_btn")]]
        await client.edit_message_caption(
            chat_id=message.chat.id,
            message_id=message.id,
            caption=script.HELP_TXT,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=enums.ParseMode.HTML
        )

    elif data == "about_btn":
        buttons = [[InlineKeyboardButton("⬅️ Back to Home", callback_data="start_btn")]]
        await client.edit_message_caption(
            chat_id=message.chat.id,
            message_id=message.id,
            caption=script.ABOUT_TXT,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=enums.ParseMode.HTML
        )

    elif data == "start_btn":
        bot  = await client.get_me()
        apis = ["https://api.waifu.pics/sfw/waifu", "https://nekos.life/api/v2/img/waifu"]
        try:
            response  = requests.get(random.choice(apis))
            response.raise_for_status()
            photo_url = response.json()["url"]
        except Exception as e:
            logger.error(f"Failed to fetch image from API: {e}")
            photo_url = "https://i.postimg.cc/cC7txyhz/15.png"

        buttons = [
            [
                InlineKeyboardButton("💎 Buy Premium", callback_data="buy_premium"),
                InlineKeyboardButton("🆘 Help & Guide", callback_data="help_btn")
            ],
            [
                InlineKeyboardButton("⚙️ Settings Panel", callback_data="settings_btn"),
                InlineKeyboardButton("ℹ️ About Bot",       callback_data="about_btn")
            ],
            [
                InlineKeyboardButton('📢 Channels',    callback_data="channels_info"),
                InlineKeyboardButton('👨‍💻 Developers', callback_data="dev_info")
            ]
        ]
        await client.edit_message_media(
            chat_id=message.chat.id,
            message_id=message.id,
            media=InputMediaPhoto(
                media=photo_url,
                caption=script.START_TXT.format(
                    callback_query.from_user.mention, bot.username, bot.first_name
                )
            ),
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data == "close_btn":
        await message.delete()

    elif data in ["cmd_list_btn", "user_stats_btn", "dump_chat_btn", "thumb_btn", "caption_btn"]:
        pass   # placeholders — implement as needed

    # Silently ignore cancel_ data here; handled by cancel_callback above
    if not data.startswith("cancel_"):
        await callback_query.answer()
