# Multilingual messages for the bot

MESSAGES = {
    "uz": {
        "welcome": """👨‍⚕️ **MedGemma Tibbiy Yordamchi - SinoAI**

Assalomu alaykum! Men Google'ning MedGemma 1.5 4B modeli asosida ishlayman.

**Qanday foydalanish:**
Menga istalgan tibbiy savolingizni yuboring yoki tibbiy rasm yuboring.

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
/clear - Suhbat tarixini tozalash

**Maslahatlar:**
✓ Aniq va ravshan savollar bering
✓ Simptomlar, davolanish, tibbiy atamalar haqida so'rashingiz mumkin
✓ Tibbiy rasmlar yuborishingiz mumkin

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
        "no_language": "Iltimos, avval /start buyrug'i orqali tilni tanlang.",
        "history_cleared": "🗑️ Suhbat tarixi tozalandi.",
        "analyze_image": "Iltimos, ushbu tibbiy tasvirni tahlil qiling."
    },

    "ru": {
        "welcome": """👨‍⚕️ **MedGemma Медицинский Ассистент - SinoAI**

Здравствуйте! Я работаю на основе модели Google MedGemma 1.5 4B.

**Как использовать:**
Отправьте мне любой медицинский вопрос или медицинское изображение.

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
/clear - Очистить историю чата

**Советы:**
✓ Задавайте чёткие, конкретные вопросы
✓ Могу помочь с симптомами, лечением, медицинскими терминами
✓ Можете отправлять медицинские изображения

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
        "no_language": "Пожалуйста, сначала выберите язык через команду /start.",
        "history_cleared": "🗑️ История чата очищена.",
        "analyze_image": "Пожалуйста, проанализируйте это медицинское изображение."
    },

    "en": {
        "welcome": """👨‍⚕️ **MedGemma Medical Assistant - SinoAI**

Hello! I'm powered by Google's MedGemma 1.5 4B model.

**How to use:**
Send me any medical question or medical image.

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
/clear - Clear chat history

**Tips:**
✓ Ask clear, specific questions
✓ I can help with symptoms, treatments, medical terms
✓ You can send medical images

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
        "no_language": "Please select a language first using the /start command.",
        "history_cleared": "🗑️ Chat history cleared.",
        "analyze_image": "Please analyze this medical image."
    }
}


def get_message(lang: str, key: str, **kwargs) -> str:
    """Get a message in the user's language"""
    msg = MESSAGES.get(lang, MESSAGES["en"]).get(key, MESSAGES["en"][key])
    if kwargs:
        msg = msg.format(**kwargs)
    return msg
