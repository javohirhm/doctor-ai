import os
import json
import base64
import logging
import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.helpers import escape_markdown
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from google.cloud import aiplatform
from google.auth import default
from google.auth.transport.requests import Request

# ==================== LOAD ENVIRONMENT VARIABLES ====================
load_dotenv()

# ==================== LOGGING ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")
ENDPOINT_ID = os.getenv("ENDPOINT_ID")
DEDICATED_ENDPOINT_DNS = os.getenv("DEDICATED_ENDPOINT_DNS")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
USER_DATA_FILE = os.getenv("USER_DATA_FILE", "users.json")

logger.info(f"✅ Project: {PROJECT_ID}")
logger.info(f"✅ Region: {LOCATION}")
logger.info(f"✅ Endpoint: {ENDPOINT_ID}")
logger.info(f"✅ Dedicated DNS: {DEDICATED_ENDPOINT_DNS}")

# ==================== USER DATA MANAGEMENT ====================

def load_users() -> dict:
    """Load user data from JSON file"""
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_users(users: dict):
    """Save user data to JSON file"""
    with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def get_user_language(user_id: int) -> str | None:
    """Get user's selected language"""
    users = load_users()
    user_data = users.get(str(user_id))
    if user_data:
        return user_data.get("language")
    return None

def set_user_language(user_id: int, language: str, first_name: str = None, username: str = None):
    """Set user's language preference"""
    users = load_users()
    user_key = str(user_id)
    if user_key not in users:
        users[user_key] = {}
    users[user_key]["language"] = language
    if first_name:
        users[user_key]["first_name"] = first_name
    if username:
        users[user_key]["username"] = username
    save_users(users)

# ==================== MULTILINGUAL CONTENT ====================

MESSAGES = {
    "uz": {
        "welcome": """👨‍⚕️ **MedGemma Tibbiy Yordamchi - SinoAI**

Assalomu alaykum! Men Google'ning MedGemma 1.5 4B modeli asosida ishlayman.

**Qanday foydalanish:**
Menga istalgan tibbiy savolingizni yuboring.

**Namuna savollar:**
- Diabet kasalligining belgilari qanday?
- Yurak xurujining alomatlari nimalar?
- Gipertoniya nima?

⚠️ **Ogohlantirish:** Bu faqat ta'lim maqsadlari uchun. Har doim malakali shifokorga murojaat qiling.

Savolingizni yozing! 🚀""",
        "help": """📖 **MedGemma Botidan Foydalanish**

Menga tibbiy savolingizni yuboring va men ma'lumot beraman!

**Buyruqlar:**
/start - Tilni tanlash
/help - Yordam
/stats - Bot statistikasi
/language - Tilni o'zgartirish

**Maslahatlar:**
✓ Aniq va ravshan savollar bering
✓ Simptomlar, davolanish, tibbiy atamalar haqida so'rashingiz mumkin

Namuna: "Yuqori qon bosimining sabablari nima?" """,
        "stats": """📊 **MedGemma Bot Statistikasi**

🤖 Model: MedGemma 1.5 4B-IT
📍 Mintaqa: {location}
✅ Holat: Faol
🏥 Maqsad: Tibbiy AI Yordamchi
🏢 Tashkilot: SinoAI

Google Cloud Vertex AI asosida ishlaydi""",
        "thinking": "O'ylayapman...",
        "error": """⚠️ Kechirasiz, xatolik yuz berdi.

Xato tafsilotlari: {error}

Iltimos, qaytadan urinib ko'ring yoki savolingizni boshqacha shakllantiring.""",
        "choose_language": "Iltimos, tilni tanlang:",
        "language_set": "✅ Til o'zbekcha qilib o'rnatildi!",
        "no_language": "Iltimos, avval /start buyrug'i orqali tilni tanlang."
    },
    "ru": {
        "welcome": """👨‍⚕️ **MedGemma Медицинский Ассистент - SinoAI**

Здравствуйте! Я работаю на основе модели Google MedGemma 1.5 4B.

**Как использовать:**
Отправьте мне любой медицинский вопрос.

**Примеры вопросов:**
- Какие симптомы диабета?
- Что такое артериальное давление?
- Признаки сердечного приступа?

⚠️ **Предупреждение:** Только для образовательных целей. Всегда консультируйтесь с врачом.

Напишите ваш вопрос! 🚀""",
        "help": """📖 **Как использовать MedGemma Bot**

Отправьте мне медицинский вопрос и я предоставлю информацию!

**Команды:**
/start - Выбор языка
/help - Эта справка
/stats - Статистика бота
/language - Изменить язык

**Советы:**
✓ Задавайте чёткие, конкретные вопросы
✓ Могу помочь с симптомами, лечением, медицинскими терминами

Пример: "Что вызывает высокое давление?" """,
        "stats": """📊 **Статистика MedGemma Bot**

🤖 Модель: MedGemma 1.5 4B-IT
📍 Регион: {location}
✅ Статус: Активен
🏥 Назначение: Медицинский AI Ассистент
🏢 Организация: SinoAI

Работает на Google Cloud Vertex AI""",
        "thinking": "Думаю...",
        "error": """⚠️ Извините, произошла ошибка.

Детали ошибки: {error}

Пожалуйста, попробуйте снова или переформулируйте вопрос.""",
        "choose_language": "Пожалуйста, выберите язык:",
        "language_set": "✅ Язык установлен на русский!",
        "no_language": "Пожалуйста, сначала выберите язык через команду /start."
    },
    "en": {
        "welcome": """👨‍⚕️ **MedGemma Medical Assistant - SinoAI**

Hello! I'm powered by Google's MedGemma 1.5 4B model.

**How to use:**
Send me any medical question.

**Example questions:**
- What are the symptoms of diabetes?
- What is hypertension?
- Signs of a heart attack?

⚠️ **Disclaimer:** This is for educational purposes only. Always consult a licensed physician.

Type your question to get started! 🚀""",
        "help": """📖 **How to Use MedGemma Bot**

Just send me your medical question and I'll provide information!

**Commands:**
/start - Choose language
/help - This help message
/stats - Bot statistics
/language - Change language

**Tips:**
✓ Ask clear, specific questions
✓ I can help with symptoms, treatments, medical terms

Example: "What causes high blood pressure?" """,
        "stats": """📊 **MedGemma Bot Statistics**

🤖 Model: MedGemma 1.5 4B-IT
📍 Region: {location}
✅ Status: Active
🏥 Purpose: Medical AI Assistant
🏢 Organization: SinoAI

Powered by Google Cloud Vertex AI""",
        "thinking": "Thinking...",
        "error": """⚠️ Sorry, an error occurred.

Error details: {error}

Please try again or rephrase your question.""",
        "choose_language": "Please choose your language:",
        "language_set": "✅ Language set to English!",
        "no_language": "Please select a language first using the /start command."
    }
}

# ==================== SYSTEM PROMPTS ====================

SYSTEM_PROMPTS = {
    "uz": """Siz shifokorlar uchun klinik qaror qabul qilishda yordam beruvchi AI yordamchisisiz.

Sizning vazifangiz:
- Litsenziyalangan tibbiyot mutaxassislariga bemor ma'lumotlarini tahlil qilishda yordam berish.
- Shifokorning maqsadini, klinik fikrlashini va tashvishlarini tushunish.
- Tuzilgan tibbiy ma'lumotlar, differensial mulohazalar va tavsiyalar berish.
- Siz shifokorni ALMASHTIRMAYSIZ va YAKUNIY TASHXIS QOYMAYSIZ.

Asosiy qoidalar (o'zgarmas):
1. Har doim foydalanuvchi SHIFOKOR yoki TIBBIYOT MUTAXASSISI deb hisoblang.
2. Hech qachon to'g'ridan-to'g'ri bemorlar bilan gaplashmang.
3. Hech qachon mutlaq tashxis qo'ymang.
4. So'ralmasa, favqulodda ko'rsatmalar bermang.
5. Har doim natijalarni klinik yordam sifatida, tibbiy hokimiyat sifatida emas, shakllantiring.

Javob formati:

---
🧠 Klinik Talqin:
(Qisqacha professional tibbiy tilda holatni tahlil qilish)

📋 Mumkin bo'lgan Mulohazalar (Tashxis emas):
- Holat 1 (qisqa asoslash)
- Holat 2 (qisqa asoslash)
- Holat 3 (ixtiyoriy)

🧪 Tavsiya etilgan Keyingi Qadamlar:
- Tavsiya etilgan laboratoriya / tasvirlash / monitoring
- Kuzatish kerak bo'lgan xavf belgilari
- Differensialni toraytirish uchun nima yordam beradi

💡 Klinik Eslatmalar:
- Tegishli ko'rsatmalar, fikrlash yoki ogohlantirishlar
- Agar tegishli bo'lsa, dori o'zaro ta'sirlari yoki qarshi ko'rsatmalar

⚠️ Ogohlantirish:
Bu ma'lumot faqat klinik qaror qabul qilishda yordam uchun mo'ljallangan va professional tibbiy fikrni almashtirmaydi.
---

Uslub va ohang:
- Professional, ixcham, dalillarga asoslangan
- O'zbek tilida javob bering
- Bemorga yo'naltirilgan tushuntirishlar bermang
- Keraksiz so'zlardan saqlaning""",

    "ru": """Вы - AI-ассистент для поддержки принятия клинических решений врачами.

Ваша роль:
- Помогать лицензированным медицинским специалистам анализировать информацию о пациентах.
- Понимать намерения врача, клиническое мышление и опасения.
- Предоставлять структурированную медицинскую информацию, дифференциальные соображения и рекомендации.
- Вы НЕ заменяете врача и НЕ ставите окончательных диагнозов.

Основные правила (неизменные):
1. Всегда предполагайте, что пользователь - ВРАЧ или МЕДИЦИНСКИЙ СПЕЦИАЛИСТ.
2. Никогда не обращайтесь напрямую к пациентам.
3. Никогда не ставьте абсолютных диагнозов.
4. Не давайте экстренных инструкций, если не попросят.
5. Всегда формулируйте выводы как клиническую поддержку, а не медицинский авторитет.

Формат ответа:

---
🧠 Клиническая Интерпретация:
(Краткий анализ случая профессиональным медицинским языком)

📋 Возможные Соображения (Не диагнозы):
- Состояние 1 (краткое обоснование)
- Состояние 2 (краткое обоснование)
- Состояние 3 (опционально)

🧪 Рекомендуемые Следующие Шаги:
- Рекомендуемые анализы / визуализация / мониторинг
- Тревожные признаки для наблюдения
- Что поможет сузить дифференциал

💡 Клинические Заметки:
- Соответствующие рекомендации, рассуждения или предостережения
- Лекарственные взаимодействия или противопоказания при необходимости

⚠️ Предупреждение:
Эта информация предназначена только для поддержки принятия клинических решений и не заменяет профессионального медицинского суждения.
---

Стиль и тон:
- Профессиональный, лаконичный, основанный на доказательствах
- Отвечайте на русском языке
- Без объяснений для пациентов
- Без лишней многословности""",

    "en": """You are a clinical decision-support AI assistant for doctors.

Your role:
- Assist licensed medical professionals by analyzing patient information.
- Understand the doctor's intent, clinical reasoning, and concerns.
- Provide structured medical insights, differential considerations, and recommendations.
- You do NOT replace a doctor and you do NOT give final diagnoses.

Core rules (non-negotiable):
1. Always assume the user is a DOCTOR or MEDICAL PROFESSIONAL.
2. Never speak directly to patients.
3. Never give absolute diagnoses.
4. Never give emergency instructions unless explicitly asked.
5. Always frame outputs as clinical support, not medical authority.

Response format:

---
🧠 Clinical Interpretation:
(Brief interpretation of the case in professional medical language)

📋 Possible Considerations (Not Diagnoses):
- Condition 1 (short rationale)
- Condition 2 (short rationale)
- Condition 3 (optional)

🧪 Suggested Next Steps:
- Recommended labs / imaging / monitoring
- Red flags to watch for
- What would help narrow the differential

💡 Clinical Notes:
- Relevant guidelines, reasoning, or cautions
- Drug interactions or contraindications if applicable

⚠️ Disclaimer:
This information is for clinical decision support only and does not replace professional medical judgment.
---

Style & tone:
- Professional, concise, evidence-aware
- Respond in English
- No patient-facing explanations
- No unnecessary verbosity"""
}

# ==================== HELPER FUNCTIONS ====================

def get_message(lang: str, key: str, **kwargs) -> str:
    """Get a message in the user's language"""
    msg = MESSAGES.get(lang, MESSAGES["en"]).get(key, MESSAGES["en"][key])
    if kwargs:
        msg = msg.format(**kwargs)
    return msg

def call_medgemma(user_message: str, language: str = "en", timeout: int = 120) -> str:
    """Call MedGemma dedicated endpoint with language-specific system prompt"""
    # Get credentials
    credentials, _ = default()
    if not credentials.valid:
        credentials.refresh(Request())

    # Use DEDICATED endpoint DNS
    url = f"https://{DEDICATED_ENDPOINT_DNS}/v1/projects/{PROJECT_ID}/locations/{LOCATION}/endpoints/{ENDPOINT_ID}:predict"

    headers = {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json"
    }

    # Get language-specific system prompt
    system_prompt = SYSTEM_PROMPTS.get(language, SYSTEM_PROMPTS["en"])

    payload = {
        "instances": [{
            "@requestFormat": "chatCompletions",
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        }]
    }

    logger.info(f"🔄 Calling dedicated endpoint (language: {language})...")

    # Make request
    response = requests.post(url, headers=headers, json=payload, timeout=timeout)

    # Check status
    if response.status_code != 200:
        logger.error(f"❌ HTTP {response.status_code}: {response.text}")
        raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")

    # Parse response
    result = response.json()

    preds = result.get("predictions")

    # Normalize predictions to a dict
    if isinstance(preds, dict):
        prediction = preds
    elif isinstance(preds, list) and preds:
        prediction = preds[0]
    else:
        return "Sorry, I couldn't generate a response."

    # Extract content
    content = None
    if isinstance(prediction, dict):
        if "choices" in prediction and prediction["choices"]:
            choice = prediction["choices"][0]
            msg = choice.get("message", {})
            if "content" in msg:
                content = msg["content"]
        if content is None and "content" in prediction:
            content = prediction["content"]
        if content is None and "text" in prediction:
            content = prediction["text"]

    if content is None:
        content = str(prediction)

    # Remove everything before <unused95> token (model's thinking process)
    if "<unused95>" in content:
        content = content.split("<unused95>", 1)[1].strip()

    return content


def call_medgemma_with_image(image_base64: str, user_message: str = None, language: str = "en", timeout: int = 120) -> str:
    """Call MedGemma dedicated endpoint with image and optional text"""
    # Get credentials
    credentials, _ = default()
    if not credentials.valid:
        credentials.refresh(Request())

    # Use DEDICATED endpoint DNS
    url = f"https://{DEDICATED_ENDPOINT_DNS}/v1/projects/{PROJECT_ID}/locations/{LOCATION}/endpoints/{ENDPOINT_ID}:predict"

    headers = {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json"
    }

    # Get language-specific system prompt
    system_prompt = SYSTEM_PROMPTS.get(language, SYSTEM_PROMPTS["en"])

    # Default message if user didn't provide caption
    if not user_message:
        default_prompts = {
            "uz": "Iltimos, ushbu tibbiy tasvirni tahlil qiling.",
            "ru": "Пожалуйста, проанализируйте это медицинское изображение.",
            "en": "Please analyze this medical image."
        }
        user_message = default_prompts.get(language, default_prompts["en"])

    # Build user content with image and text
    user_content = [
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{image_base64}"
            }
        },
        {
            "type": "text",
            "text": user_message
        }
    ]

    payload = {
        "instances": [{
            "@requestFormat": "chatCompletions",
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_content
                }
            ]
        }]
    }

    logger.info(f"🔄 Calling dedicated endpoint with image (language: {language})...")

    # Make request
    response = requests.post(url, headers=headers, json=payload, timeout=timeout)

    # Check status
    if response.status_code != 200:
        logger.error(f"❌ HTTP {response.status_code}: {response.text}")
        raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")

    # Parse response
    result = response.json()

    preds = result.get("predictions")

    # Normalize predictions to a dict
    if isinstance(preds, dict):
        prediction = preds
    elif isinstance(preds, list) and preds:
        prediction = preds[0]
    else:
        return "Sorry, I couldn't generate a response."

    # Extract content
    content = None
    if isinstance(prediction, dict):
        if "choices" in prediction and prediction["choices"]:
            choice = prediction["choices"][0]
            msg = choice.get("message", {})
            if "content" in msg:
                content = msg["content"]
        if content is None and "content" in prediction:
            content = prediction["content"]
        if content is None and "text" in prediction:
            content = prediction["text"]

    if content is None:
        content = str(prediction)

    # Remove everything before <unused95> token (model's thinking process)
    if "<unused95>" in content:
        content = content.split("<unused95>", 1)[1].strip()

    return content

# ==================== TELEGRAM HANDLERS ====================

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
        # Call MedGemma with user's language
        logger.info("🔄 Calling MedGemma endpoint...")
        response_text = call_medgemma(user_message, language=lang)

        logger.info(f"✅ Response received ({len(response_text)} chars)")

        # Send response to user
        safe_text = escape_markdown(response_text, version=2)
        if len(response_text) > 4000:
            # Split long messages
            for i in range(0, len(safe_text), 4000):
                await update.message.reply_text(
                    safe_text[i:i+4000],
                    parse_mode="MarkdownV2"
                )
        else:
            await update.message.reply_text(
                safe_text,
                parse_mode="MarkdownV2"
            )

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

        logger.info(f"🔄 Calling MedGemma endpoint with image...")
        response_text = call_medgemma_with_image(image_base64, caption, language=lang)

        logger.info(f"✅ Response received ({len(response_text)} chars)")

        # Send response to user
        safe_text = escape_markdown(response_text, version=2)
        if len(response_text) > 4000:
            # Split long messages
            for i in range(0, len(safe_text), 4000):
                await update.message.reply_text(
                    safe_text[i:i+4000],
                    parse_mode="MarkdownV2"
                )
        else:
            await update.message.reply_text(
                safe_text,
                parse_mode="MarkdownV2"
            )

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


# ==================== MAIN ====================

def main():
    """Start the bot"""

    if not TELEGRAM_TOKEN:
        raise ValueError("❌ TELEGRAM_BOT_TOKEN environment variable not set!")

    logger.info("=" * 60)
    logger.info("🚀 Starting MedGemma Telegram Bot for SinoAI")
    logger.info("=" * 60)
    logger.info(f"Project: {PROJECT_ID}")
    logger.info(f"Region: {LOCATION}")
    logger.info(f"Endpoint: {ENDPOINT_ID}")
    logger.info(f"User data file: {USER_DATA_FILE}")
    logger.info("=" * 60)

    # Create application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("language", language_command))

    # Add callback handler for language selection
    application.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))

    # Add message handler for questions
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Add handler for images
    application.add_handler(
        MessageHandler(filters.PHOTO, handle_image)
    )

    # Start polling
    logger.info("✅ Bot is running! Doctors can now ask questions.")
    logger.info("Press Ctrl+C to stop the bot")
    logger.info("=" * 60)

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
