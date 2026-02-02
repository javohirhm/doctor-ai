import base64
import hashlib
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from .config import LOCATION, logger
from .database import (
    get_user_language, set_user_language,
    get_conversation_history, add_message, clear_user_history,
    store_suggestion, get_suggestion
)
from .messages import get_message
from .medgemma import call_medgemma, call_medgemma_with_image
from .gemini import generate_suggestions, translate_uz_to_en, translate_en_to_uz, transcribe_audio


async def send_markdown_message(message, text, reply_markup=None):
    """Send message with Markdown formatting, fallback to plain text if error"""
    try:
        return await message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.warning(f"⚠️ Markdown parse failed, sending plain text: {e}")
        return await message.reply_text(
            text,
            reply_markup=reply_markup
        )


def get_language_keyboard() -> InlineKeyboardMarkup:
    """Create language selection keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="lang_uz"),
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_suggestion_keyboard(suggestions: list, user_id: int) -> InlineKeyboardMarkup | None:
    """Create keyboard with follow-up suggestion buttons"""
    if not suggestions:
        return None

    keyboard = []
    for i, suggestion in enumerate(suggestions[:2]):  # Max 2 suggestions
        # Create a short hash for callback data (Telegram limits callback_data to 64 bytes)
        suggestion_id = hashlib.md5(f"{user_id}_{i}_{suggestion}".encode()).hexdigest()[:12]
        # Store the full suggestion text in database
        store_suggestion(suggestion_id, suggestion)
        keyboard.append([InlineKeyboardButton(f"💬 {suggestion}", callback_data=f"suggest_{suggestion_id}")])

    return InlineKeyboardMarkup(keyboard) if keyboard else None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message with language selection"""
    user_id = update.effective_user.id
    lang = get_user_language(user_id)

    if lang:
        # User exists, send welcome message in their language
        await update.message.reply_text(get_message(lang, "welcome"), parse_mode='Markdown')
    else:
        # New user, ask for language
        await update.message.reply_text(
            "🌐 Please choose your language / Tilni tanlang / Выберите язык:",
            reply_markup=get_language_keyboard()
        )


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Change language command"""
    await update.message.reply_text(
        "🌐 Please choose your language / Tilni tanlang / Выберите язык:",
        reply_markup=get_language_keyboard()
    )


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle language selection callback"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    first_name = query.from_user.first_name
    username = query.from_user.username

    # Extract language from callback data
    lang = query.data.replace("lang_", "")

    # Save user language
    set_user_language(user_id, lang, first_name, username)

    logger.info(f"👤 User {first_name} (ID:{user_id}) selected language: {lang}")

    # Send confirmation and welcome message
    await query.edit_message_text(get_message(lang, "language_set"))
    await query.message.reply_text(get_message(lang, "welcome"), parse_mode='Markdown')


async def suggestion_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle suggestion button press - sends the suggestion as a new message to MedGemma"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user_name = query.from_user.first_name

    # Extract suggestion ID from callback data
    suggestion_id = query.data.replace("suggest_", "")

    # Get the full suggestion text from database
    suggestion_text = get_suggestion(suggestion_id)

    if not suggestion_text:
        logger.warning(f"⚠️ Suggestion not found: {suggestion_id}")
        return

    lang = get_user_language(user_id)
    if not lang:
        return

    logger.info(f"📩 Suggestion selected by {user_name} (ID:{user_id}): {suggestion_text[:50]}...")

    # Replace the buttons with the selected question text (shows what user chose)
    try:
        # Get the original message text and append the user's selection
        original_text = query.message.text or ""
        # Add a separator and the selected question
        updated_text = f"{original_text}\n\n➡️ {suggestion_text}"
        await query.edit_message_text(text=updated_text, reply_markup=None)
    except Exception as e:
        logger.warning(f"⚠️ Could not edit message: {e}")
        # Fallback: just remove buttons
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass

    # Send a "thinking" message
    thinking_msg = await query.message.reply_text(get_message(lang, "thinking"))

    try:
        # Get conversation history
        history = get_conversation_history(user_id)

        # For Uzbek: translate suggestion to English before sending to MedGemma
        message_for_medgemma = suggestion_text
        medgemma_lang = lang
        if lang == "uz":
            message_for_medgemma = translate_uz_to_en(suggestion_text)
            medgemma_lang = "en"  # Use English prompt for MedGemma

        # Call MedGemma with the suggestion as the new message
        logger.info("🔄 Calling MedGemma endpoint with suggestion...")
        response_text = call_medgemma(message_for_medgemma, language=medgemma_lang, history=history)

        logger.info(f"✅ Response received ({len(response_text)} chars)")

        # For Uzbek: translate response back to Uzbek
        if lang == "uz":
            response_text = translate_en_to_uz(response_text)

        # Save messages to history (save in user's language)
        add_message(user_id, "user", suggestion_text)
        add_message(user_id, "assistant", response_text)

        # Generate new suggestions
        suggestions = generate_suggestions(suggestion_text, response_text, language=lang)
        suggestion_keyboard = create_suggestion_keyboard(suggestions, user_id)

        # Send response with new suggestion buttons (Markdown with fallback)
        if len(response_text) > 4000:
            # Split long messages, add buttons to last one
            chunks = [response_text[i:i+4000] for i in range(0, len(response_text), 4000)]
            for i, chunk in enumerate(chunks):
                if i == len(chunks) - 1:  # Last chunk
                    await send_markdown_message(query.message, chunk, reply_markup=suggestion_keyboard)
                else:
                    await send_markdown_message(query.message, chunk)
        else:
            await send_markdown_message(query.message, response_text, reply_markup=suggestion_keyboard)

    except Exception as e:
        logger.error(f"❌ Error: {str(e)}", exc_info=True)
        error_msg = get_message(lang, "error", error=str(e)[:200])
        await query.message.reply_text(error_msg)
    finally:
        # Cleanup thinking message
        try:
            await thinking_msg.delete()
        except Exception:
            pass


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help message in user's language"""
    user_id = update.effective_user.id
    lang = get_user_language(user_id)

    if not lang:
        await update.message.reply_text(
            "Please select a language first / Avval tilni tanlang / Сначала выберите язык",
            reply_markup=get_language_keyboard()
        )
        return

    await update.message.reply_text(get_message(lang, "help"), parse_mode='Markdown')


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics in user's language"""
    user_id = update.effective_user.id
    lang = get_user_language(user_id)

    if not lang:
        await update.message.reply_text(
            "Please select a language first / Avval tilni tanlang / Сначала выберите язык",
            reply_markup=get_language_keyboard()
        )
        return

    stats = get_message(lang, "stats", location=LOCATION)
    await update.message.reply_text(stats, parse_mode='Markdown')


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear conversation history"""
    user_id = update.effective_user.id
    lang = get_user_language(user_id)

    if not lang:
        await update.message.reply_text(
            "Please select a language first / Avval tilni tanlang / Сначала выберите язык",
            reply_markup=get_language_keyboard()
        )
        return

    clear_user_history(user_id)
    await update.message.reply_text(get_message(lang, "history_cleared"))


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle medical questions from users"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    user_message = update.message.text

    # Check if user has selected a language
    lang = get_user_language(user_id)

    if not lang:
        await update.message.reply_text(
            "Please select a language first / Avval tilni tanlang / Сначала выберите язык",
            reply_markup=get_language_keyboard()
        )
        return

    logger.info(f"📩 Question from {user_name} (ID:{user_id}, lang:{lang}): {user_message[:50]}...")

    # Show typing indicator and send a temporary "thinking" message
    await update.message.chat.send_action(action="typing")
    thinking_msg = await update.message.reply_text(get_message(lang, "thinking"))

    try:
        # Get conversation history
        history = get_conversation_history(user_id)

        # For Uzbek: translate to English before sending to MedGemma
        message_for_medgemma = user_message
        medgemma_lang = lang
        if lang == "uz":
            message_for_medgemma = translate_uz_to_en(user_message)
            medgemma_lang = "en"  # Use English prompt for MedGemma

        # Call MedGemma with user's language and history
        logger.info("🔄 Calling MedGemma endpoint...")
        response_text = call_medgemma(message_for_medgemma, language=medgemma_lang, history=history)

        logger.info(f"✅ Response received ({len(response_text)} chars)")

        # For Uzbek: translate response back to Uzbek
        if lang == "uz":
            response_text = translate_en_to_uz(response_text)

        # Save messages to history (save in user's language)
        add_message(user_id, "user", user_message)
        add_message(user_id, "assistant", response_text)

        # Generate follow-up suggestions using Gemini
        suggestions = generate_suggestions(user_message, response_text, language=lang)
        suggestion_keyboard = create_suggestion_keyboard(suggestions, user_id)

        # Send response to user with suggestion buttons (Markdown with fallback)
        if len(response_text) > 4000:
            # Split long messages, add buttons to last one
            chunks = [response_text[i:i+4000] for i in range(0, len(response_text), 4000)]
            for i, chunk in enumerate(chunks):
                if i == len(chunks) - 1:  # Last chunk
                    await send_markdown_message(update.message, chunk, reply_markup=suggestion_keyboard)
                else:
                    await send_markdown_message(update.message, chunk)
        else:
            await send_markdown_message(update.message, response_text, reply_markup=suggestion_keyboard)

    except Exception as e:
        logger.error(f"❌ Error: {str(e)}", exc_info=True)
        error_msg = get_message(lang, "error", error=str(e)[:200])
        await update.message.reply_text(error_msg)
    finally:
        # Best-effort cleanup of the temporary thinking message
        try:
            await thinking_msg.delete()
        except Exception:
            pass


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages from users"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    lang = get_user_language(user_id)
    if not lang:
        await update.message.reply_text(
            "Please select a language first / Avval tilni tanlang / Сначала выберите язык",
            reply_markup=get_language_keyboard()
        )
        return

    voice = update.message.voice
    if not voice:
        await update.message.reply_text(get_message(lang, "no_transcript"))
        return

    logger.info(f"🎤 Voice from {user_name} (ID:{user_id}, lang:{lang}), duration: {voice.duration}s")

    await update.message.chat.send_action(action="typing")
    status_msg = await update.message.reply_text(get_message(lang, "transcribing"))

    try:
        voice_file = await context.bot.get_file(voice.file_id)
        audio_bytes = await voice_file.download_as_bytearray()
        mime_type = voice.mime_type or "audio/ogg"

        transcript = transcribe_audio(
            audio_bytes=audio_bytes,
            mime_type=mime_type,
            language_hint=lang
        ).strip()

        if not transcript:
            await update.message.reply_text(get_message(lang, "no_transcript"))
            return

        try:
            await status_msg.edit_text(get_message(lang, "thinking"))
        except Exception:
            pass

        history = get_conversation_history(user_id)

        message_for_medgemma = transcript
        medgemma_lang = lang
        if lang == "uz":
            message_for_medgemma = translate_uz_to_en(transcript)
            medgemma_lang = "en"

        logger.info("🔄 Calling MedGemma endpoint (voice transcript)...")
        response_text = call_medgemma(message_for_medgemma, language=medgemma_lang, history=history)

        logger.info(f"✅ Response received ({len(response_text)} chars)")

        if lang == "uz":
            response_text = translate_en_to_uz(response_text)

        add_message(user_id, "user", transcript)
        add_message(user_id, "assistant", response_text)

        suggestions = generate_suggestions(transcript, response_text, language=lang)
        suggestion_keyboard = create_suggestion_keyboard(suggestions, user_id)

        if len(response_text) > 4000:
            chunks = [response_text[i:i+4000] for i in range(0, len(response_text), 4000)]
            for i, chunk in enumerate(chunks):
                if i == len(chunks) - 1:
                    await send_markdown_message(update.message, chunk, reply_markup=suggestion_keyboard)
                else:
                    await send_markdown_message(update.message, chunk)
        else:
            await send_markdown_message(update.message, response_text, reply_markup=suggestion_keyboard)

    except Exception as e:
        logger.error(f"❌ Error: {str(e)}", exc_info=True)
        error_msg = get_message(lang, "error", error=str(e)[:200])
        await update.message.reply_text(error_msg)
    finally:
        try:
            await status_msg.delete()
        except Exception:
            pass


async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle medical images from users"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    # Check if user has selected a language
    lang = get_user_language(user_id)

    if not lang:
        await update.message.reply_text(
            "Please select a language first / Avval tilni tanlang / Сначала выберите язык",
            reply_markup=get_language_keyboard()
        )
        return

    # Get caption if provided
    caption = update.message.caption or ""

    logger.info(f"🖼️ Image from {user_name} (ID:{user_id}, lang:{lang}), caption: {caption[:50] if caption else 'None'}...")

    # Show typing indicator and send a temporary "thinking" message
    await update.message.chat.send_action(action="typing")
    thinking_msg = await update.message.reply_text(get_message(lang, "thinking"))

    try:
        # Get the largest photo (best quality)
        photo = update.message.photo[-1]

        # Download the photo
        photo_file = await context.bot.get_file(photo.file_id)
        image_bytes = await photo_file.download_as_bytearray()

        # Convert to base64
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        # Get conversation history
        history = get_conversation_history(user_id)

        # For Uzbek: translate caption to English before sending to MedGemma
        caption_for_medgemma = caption
        medgemma_lang = lang
        if lang == "uz" and caption:
            caption_for_medgemma = translate_uz_to_en(caption)
            medgemma_lang = "en"  # Use English prompt for MedGemma
        elif lang == "uz":
            medgemma_lang = "en"

        logger.info("🔄 Calling MedGemma endpoint with image...")
        response_text = call_medgemma_with_image(
            image_base64, caption_for_medgemma, language=medgemma_lang, history=history
        )

        logger.info(f"✅ Response received ({len(response_text)} chars)")

        # For Uzbek: translate response back to Uzbek
        if lang == "uz":
            response_text = translate_en_to_uz(response_text)

        # Save to history (store caption or default message, not the image)
        user_msg = caption or get_message(lang, "analyze_image")
        add_message(user_id, "user", f"[Image] {user_msg}")
        add_message(user_id, "assistant", response_text)

        # Generate follow-up suggestions using Gemini
        suggestions = generate_suggestions(user_msg, response_text, language=lang)
        suggestion_keyboard = create_suggestion_keyboard(suggestions, user_id)

        # Send response to user with suggestion buttons (Markdown with fallback)
        if len(response_text) > 4000:
            # Split long messages, add buttons to last one
            chunks = [response_text[i:i+4000] for i in range(0, len(response_text), 4000)]
            for i, chunk in enumerate(chunks):
                if i == len(chunks) - 1:  # Last chunk
                    await send_markdown_message(update.message, chunk, reply_markup=suggestion_keyboard)
                else:
                    await send_markdown_message(update.message, chunk)
        else:
            await send_markdown_message(update.message, response_text, reply_markup=suggestion_keyboard)

    except Exception as e:
        logger.error(f"❌ Error: {str(e)}", exc_info=True)
        error_msg = get_message(lang, "error", error=str(e)[:200])
        await update.message.reply_text(error_msg)
    finally:
        # Best-effort cleanup of the temporary thinking message
        try:
            await thinking_msg.delete()
        except Exception:
            pass
