# cantarella
# Auto Rename (trigger_word -> auto_rename_format) feature
# /setformat  - interactively save a new trigger_word + format pair
# /seeformat  - list every saved trigger_word/format pair
# /delformat  - delete a saved trigger_word
#
# NOTE: This intentionally does NOT use client.listen(). Different
# pyrofork/pyrogram builds implement listen() with different signatures
# (or not at all), which caused /setformat to fail instantly and show a
# false "timed out" message. Instead we track conversation state ourselves
# in PENDING_SETFORMAT and pick up the user's next text message with a
# dedicated, high-priority handler.

from pyrogram import Client, filters, enums
from pyrogram.types import Message
from database.db import db

# user_id -> {"step": 1 or 2, "trigger": str}  (trigger only present once step 1 is done)
PENDING_SETFORMAT = {}

STEP1_PROMPT = (
    "<b>🔤 Step 1/2 — Trigger Word</b>\n\n"
    "Send the keyword/phrase that should trigger this format.\n"
    "This is matched (case-insensitive) against the incoming file's name.\n\n"
    "<i>Example:</i> <code>Crazy Love Moo</code>\n\n"
    "Send /cancel to abort."
)

STEP2_PROMPT_TEMPLATE = (
    "<b>✏️ Step 2/2 — Auto Rename Format</b>\n\n"
    "Trigger word saved: <code>{trigger}</code>\n\n"
    "Now send the rename format to use whenever a file's name matches "
    "this trigger word.\n\n"
    "<b>Supported Placeholders:</b>\n"
    "• <code>{{season}}</code> : Detected Season Number\n"
    "• <code>{{episode}}</code> : Detected Episode Number\n"
    "• <code>{{quality}}</code> : Detected Quality (e.g. 720p)\n\n"
    "<i>Example:</i>\n"
    "<code>E{{episode}}.Crazy.Love.Moo.Moo.2026.{{quality}}.ViU.WEBDL.@BLRealm.mkv</code>\n\n"
    "Send /cancel to abort."
)


# ======================================================
# /setformat - Step 1: start the conversation
# ======================================================
@Client.on_message(filters.command("setformat") & filters.private)
async def set_format_start(client: Client, message: Message):
    user_id = message.from_user.id

    if not await db.is_user_exist(user_id):
        await db.add_user(user_id, message.from_user.first_name)

    if user_id in PENDING_SETFORMAT:
        return await message.reply_text(
            "<b>⚠️ You already have a /setformat in progress.</b>\n\n"
            "Send /cancel to abort it, or continue replying to the last prompt.",
            parse_mode=enums.ParseMode.HTML
        )

    PENDING_SETFORMAT[user_id] = {"step": 1}
    await message.reply_text(STEP1_PROMPT, parse_mode=enums.ParseMode.HTML)


# ======================================================
# Catches the user's replies while /setformat is in progress.
# Registered in its own dedicated group (-10) so it can't be shadowed by
# other broad private-message handlers (e.g. bot.py's new-user-log handler
# also sits at group=-1 and matches almost every private message, which
# would otherwise "win" that group before ours is even checked).
# ======================================================
@Client.on_message(filters.private & filters.text & ~filters.command("setformat"), group=-10)
async def set_format_progress(client: Client, message: Message):
    user_id = message.from_user.id

    state = PENDING_SETFORMAT.get(user_id)
    if not state:
        return  # not mid-conversation, let other handlers process this message

    text = (message.text or "").strip()

    if text.lower() == "/cancel":
        PENDING_SETFORMAT.pop(user_id, None)
        await message.reply_text("<b>❌ Cancelled.</b>", parse_mode=enums.ParseMode.HTML)
        message.stop_propagation()

    if not text:
        await message.reply_text("<b>⚠️ Empty message, please try again (or /cancel).</b>", parse_mode=enums.ParseMode.HTML)
        message.stop_propagation()

    if state["step"] == 1:
        state["trigger"] = text
        state["step"] = 2
        await message.reply_text(
            STEP2_PROMPT_TEMPLATE.format(trigger=text),
            parse_mode=enums.ParseMode.HTML
        )
        message.stop_propagation()

    elif state["step"] == 2:
        trigger_word = state["trigger"]
        rename_format = text

        await db.set_auto_rename_format(user_id, trigger_word, rename_format)
        PENDING_SETFORMAT.pop(user_id, None)

        await message.reply_text(
            "<b>✅ Auto Rename Format Saved!</b>\n\n"
            f"<b>Trigger Word:</b> <code>{trigger_word}</code>\n"
            f"<b>Format:</b> <code>{rename_format}</code>\n\n"
            "<i>Any file whose name contains this trigger word will now be "
            "renamed using this format. Use /seeformat to view all saved "
            "formats or /delformat to remove one.</i>",
            parse_mode=enums.ParseMode.HTML
        )
        message.stop_propagation()


# ======================================================
# /seeformat - List all trigger_word/format pairs
# ======================================================
@Client.on_message(filters.command("seeformat") & filters.private)
async def see_format(client: Client, message: Message):
    user_id = message.from_user.id

    if not await db.is_user_exist(user_id):
        await db.add_user(user_id, message.from_user.first_name)

    formats = await db.get_auto_rename_formats(user_id)

    if not formats:
        return await message.reply_text(
            "<b>❌ No Auto Rename Formats Set</b>\n\n"
            "<i>Use /setformat to add one. Files that don't match any "
            "trigger word will use the default cleanup/prefix/suffix rules.</i>",
            parse_mode=enums.ParseMode.HTML
        )

    lines = ["<b>📋 Your Auto Rename Formats</b>\n"]
    for i, entry in enumerate(formats.values(), start=1):
        trigger = entry.get('trigger', '')
        fmt = entry.get('format', '')
        lines.append(
            f"<b>{i}.</b> Trigger: <code>{trigger}</code>\n"
            f"    Format: <code>{fmt}</code>"
        )
    lines.append("\n<i>Use /delformat {trigger_word} to remove one.</i>")

    await message.reply_text("\n".join(lines), parse_mode=enums.ParseMode.HTML)


# ======================================================
# /delformat {trigger_word} - Delete a saved format
# ======================================================
@Client.on_message(filters.command("delformat") & filters.private)
async def del_format(client: Client, message: Message):
    user_id = message.from_user.id

    if not await db.is_user_exist(user_id):
        await db.add_user(user_id, message.from_user.first_name)

    if len(message.command) < 2:
        return await message.reply_text(
            "<b>⚠️ Usage Error</b>\n\n"
            "<code>/delformat trigger_word</code>\n\n"
            "<i>Use /seeformat to see the exact trigger words you've saved.</i>",
            parse_mode=enums.ParseMode.HTML
        )

    trigger_word = message.text.split(" ", 1)[1].strip()
    existed = await db.delete_auto_rename_format(user_id, trigger_word)

    if existed:
        await message.reply_text(
            f"<b>🗑 Removed Auto Rename Format</b>\n\nTrigger word: <code>{trigger_word}</code>",
            parse_mode=enums.ParseMode.HTML
        )
    else:
        await message.reply_text(
            f"<b>⚠️ No format found for trigger word:</b> <code>{trigger_word}</code>\n\n"
            "<i>Use /seeformat to see the exact trigger words you've saved.</i>",
            parse_mode=enums.ParseMode.HTML
        )
