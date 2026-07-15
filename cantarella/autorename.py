# cantarella
# Auto Rename (trigger_word -> auto_rename_format) feature
# /setformat  - interactively save a new trigger_word + format pair
# /seeformat  - list every saved trigger_word/format pair
# /delformat  - delete a saved trigger_word

import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from database.db import db

# Users currently mid-way through the /setformat conversation, so a stray
# text message from them isn't picked up by any other handler.
PENDING_SETFORMAT = set()

LISTEN_TIMEOUT = 120  # seconds to wait for each reply


async def _ask(client: Client, chat_id: int, prompt: str):
    """Send a prompt and wait for the user's next text reply."""
    await client.send_message(chat_id, prompt, parse_mode=enums.ParseMode.HTML)
    try:
        reply: Message = await client.listen(chat_id, filters=filters.text, timeout=LISTEN_TIMEOUT)
        return reply
    except asyncio.TimeoutError:
        return None
    except Exception:
        return None


# ======================================================
# /setformat - Set a trigger_word + auto_rename_format pair
# ======================================================
@Client.on_message(filters.command("setformat") & filters.private)
async def set_format(client: Client, message: Message):
    user_id = message.from_user.id

    if not await db.is_user_exist(user_id):
        await db.add_user(user_id, message.from_user.first_name)

    if user_id in PENDING_SETFORMAT:
        return await message.reply_text(
            "<b>⚠️ You already have a /setformat in progress.</b>\n\n"
            "Finish or let it time out before starting a new one.",
            parse_mode=enums.ParseMode.HTML
        )

    PENDING_SETFORMAT.add(user_id)
    try:
        # ── Step 1: ask for the trigger word ─────────────────────────────
        step1 = await _ask(
            client, message.chat.id,
            "<b>🔤 Step 1/2 — Trigger Word</b>\n\n"
            "Send the keyword/phrase that should trigger this format.\n"
            "This is matched (case-insensitive) against the incoming file's name.\n\n"
            "<i>Example:</i> <code>Crazy Love Moo</code>\n\n"
            "Send /cancel to abort."
        )
        if step1 is None:
            PENDING_SETFORMAT.discard(user_id)
            return await message.reply_text(
                "<b>⌛ Timed out waiting for the trigger word.</b> Please run /setformat again.",
                parse_mode=enums.ParseMode.HTML
            )
        if not step1.text:
            PENDING_SETFORMAT.discard(user_id)
            return await step1.reply_text("<b>⚠️ Please send text. Run /setformat again.</b>", parse_mode=enums.ParseMode.HTML)
        if step1.text.strip().lower() == "/cancel":
            PENDING_SETFORMAT.discard(user_id)
            return await step1.reply_text("<b>❌ Cancelled.</b>", parse_mode=enums.ParseMode.HTML)

        trigger_word = step1.text.strip()
        if not trigger_word:
            PENDING_SETFORMAT.discard(user_id)
            return await step1.reply_text("<b>⚠️ Empty trigger word. Please run /setformat again.</b>", parse_mode=enums.ParseMode.HTML)

        # ── Step 2: ask for the auto rename format ───────────────────────
        step2 = await _ask(
            client, message.chat.id,
            "<b>✏️ Step 2/2 — Auto Rename Format</b>\n\n"
            f"Trigger word saved: <code>{trigger_word}</code>\n\n"
            "Now send the rename format to use whenever a file's name matches "
            "this trigger word.\n\n"
            "<b>Supported Placeholders:</b>\n"
            "• <code>{season}</code> : Detected Season Number\n"
            "• <code>{episode}</code> : Detected Episode Number\n"
            "• <code>{quality}</code> : Detected Quality (e.g. 720p)\n\n"
            "<i>Example:</i>\n"
            "<code>E{episode}.Crazy.Love.Moo.Moo.2026.{quality}.ViU.WEBDL.@BLRealm.mkv</code>\n\n"
            "Send /cancel to abort."
        )
        if step2 is None:
            PENDING_SETFORMAT.discard(user_id)
            return await message.reply_text(
                "<b>⌛ Timed out waiting for the format.</b> Please run /setformat again.",
                parse_mode=enums.ParseMode.HTML
            )
        if not step2.text:
            PENDING_SETFORMAT.discard(user_id)
            return await step2.reply_text("<b>⚠️ Please send text. Run /setformat again.</b>", parse_mode=enums.ParseMode.HTML)
        if step2.text.strip().lower() == "/cancel":
            PENDING_SETFORMAT.discard(user_id)
            return await step2.reply_text("<b>❌ Cancelled.</b>", parse_mode=enums.ParseMode.HTML)

        rename_format = step2.text.strip()
        if not rename_format:
            PENDING_SETFORMAT.discard(user_id)
            return await step2.reply_text("<b>⚠️ Empty format. Please run /setformat again.</b>", parse_mode=enums.ParseMode.HTML)

        # ── Save ──────────────────────────────────────────────────────────
        await db.set_auto_rename_format(user_id, trigger_word, rename_format)

        await step2.reply_text(
            "<b>✅ Auto Rename Format Saved!</b>\n\n"
            f"<b>Trigger Word:</b> <code>{trigger_word}</code>\n"
            f"<b>Format:</b> <code>{rename_format}</code>\n\n"
            "<i>Any file whose name contains this trigger word will now be "
            "renamed using this format. Use /seeformat to view all saved "
            "formats or /delformat to remove one.</i>",
            parse_mode=enums.ParseMode.HTML
        )
    finally:
        PENDING_SETFORMAT.discard(user_id)


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
