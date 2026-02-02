import base64
import requests
import json
import re
from .config import GEMINI_API_KEY, logger


# ==================== TRANSLATION FUNCTIONS ====================

def translate_uz_to_en(text: str) -> str:
    """Translate Uzbek text to English using Gemini"""
    if not GEMINI_API_KEY:
        logger.warning("⚠️ GEMINI_API_KEY not set, skipping translation")
        return text

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

        prompt = f"""Translate the following Uzbek medical text to English.
Keep medical terminology accurate. Return ONLY the translated text, nothing else.

Uzbek text:
{text}"""

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 1000,
                "thinkingConfig": {
                    "thinkingBudget": 0
                }
            }
        }

        logger.info("🔄 Translating Uzbek → English...")
        response = requests.post(url, json=payload, timeout=30)

        if response.status_code != 200:
            logger.error(f"❌ Translation API error: {response.status_code}")
            return text

        result = response.json()
        candidates = result.get("candidates", [])
        if not candidates:
            return text

        parts = candidates[0].get("content", {}).get("parts", [])

        # Get text from parts (skip thinking parts with "thought" key)
        translated = ""
        for part in parts:
            if "thought" in part:
                continue
            if "text" in part:
                translated = part.get("text", "").strip()

        if translated:
            logger.info(f"✅ Translated to English: {translated[:100]}...")
            return translated
        return text

    except Exception as e:
        logger.error(f"❌ Translation error: {e}")
        return text


def translate_en_to_uz(text: str) -> str:
    """Translate English text to Uzbek using Gemini"""
    if not GEMINI_API_KEY:
        logger.warning("⚠️ GEMINI_API_KEY not set, skipping translation")
        return text

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

        prompt = f"""Translate the following English medical text to Uzbek (Latin script).
Keep medical terminology accurate. Keep the same formatting (emojis, line breaks, sections).
Return ONLY the translated text, nothing else.

English text:
{text}"""

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 2000,
                "thinkingConfig": {
                    "thinkingBudget": 0
                }
            }
        }

        logger.info("🔄 Translating English → Uzbek...")
        response = requests.post(url, json=payload, timeout=60)

        if response.status_code != 200:
            logger.error(f"❌ Translation API error: {response.status_code}")
            return text

        result = response.json()
        candidates = result.get("candidates", [])
        if not candidates:
            return text

        parts = candidates[0].get("content", {}).get("parts", [])

        # Get text from parts (skip thinking parts with "thought" key)
        translated = ""
        for part in parts:
            if "thought" in part:
                continue
            if "text" in part:
                translated = part.get("text", "").strip()

        if translated:
            logger.info(f"✅ Translated to Uzbek: {translated[:100]}...")
            return translated
        return text

    except Exception as e:
        logger.error(f"❌ Translation error: {e}")
        return text


# ==================== SPEECH TO TEXT ====================

def transcribe_audio(audio_bytes: bytes, mime_type: str = "audio/ogg", language_hint: str | None = None) -> str:
    """Transcribe audio to text using Gemini"""
    if not GEMINI_API_KEY:
        logger.warning("⚠️ GEMINI_API_KEY not set, skipping transcription")
        return ""

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

        lang_line = f"Language hint: {language_hint}." if language_hint else ""
        prompt = (
            "Transcribe the following medical voice message. "
            "Return ONLY the transcript text, nothing else. "
            "Keep medical terminology accurate. "
            f"{lang_line}"
        ).strip()

        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime_type, "data": audio_b64}}
                ]
            }],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1024,
                "thinkingConfig": {
                    "thinkingBudget": 0
                }
            }
        }

        logger.info("🔄 Transcribing audio with Gemini 2.5 Flash...")
        response = requests.post(url, json=payload, timeout=60)

        if response.status_code != 200:
            logger.error(f"❌ Transcription API error: {response.status_code} - {response.text[:500]}")
            return ""

        result = response.json()
        candidates = result.get("candidates", [])
        if not candidates:
            logger.error("❌ No candidates in transcription response")
            return ""

        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            logger.error("❌ No parts in transcription response")
            return ""

        transcript_parts = []
        for part in parts:
            if "thought" in part:
                continue
            if "text" in part:
                transcript_parts.append(part.get("text", ""))

        transcript = "\n".join(transcript_parts).strip()
        if transcript:
            logger.info(f"✅ Transcription complete: {transcript[:100]}...")
        return transcript

    except Exception as e:
        logger.error(f"❌ Transcription error: {e}", exc_info=True)
        return ""


# ==================== SUGGESTION PROMPTS ====================

SUGGESTION_PROMPTS = {
    "uz": """Siz klinik yordamchisiz. Shifokor va tibbiy AI o'rtasidagi suhbatni tahlil qiling.

Shifokor:
{user_message}

Tibbiy AI javobi:
{assistant_response}

Shifokor sifatida keyingi mantiqiy 2 ta savol yozing. Savollar quyidagilar haqida bo'lishi mumkin:
- Tashxisni aniqlashtirish
- Davolash rejasi yoki dori dozalari
- Qaysi tekshiruvlar kerak
- Boshqa differensial tashxislar
- Xavf omillari yoki ogohlantirish belgilari

Qisqa, professional savollar yozing (har biri 50 belgigacha).

Faqat JSON formatida:
{{"suggestions": ["savol 1", "savol 2"]}}""",

    "ru": """Вы клинический ассистент. Проанализируйте диалог между врачом и медицинским AI.

Врач:
{user_message}

Ответ медицинского AI:
{assistant_response}

Напишите 2 логичных следующих вопроса от лица врача. Вопросы могут касаться:
- Уточнения диагноза
- Плана лечения или дозировки препаратов
- Какие анализы/обследования нужны
- Других дифференциальных диагнозов
- Факторов риска или тревожных признаков

Короткие, профессиональные вопросы (до 50 символов каждый).

Только JSON формат:
{{"suggestions": ["вопрос 1", "вопрос 2"]}}""",

    "en": """You are a clinical assistant. Analyze this conversation between a doctor and medical AI.

Doctor:
{user_message}

Medical AI response:
{assistant_response}

Write 2 logical follow-up questions the doctor might ask. Questions can be about:
- Clarifying the diagnosis
- Treatment plan or medication dosages
- Which tests/investigations are needed
- Other differential diagnoses to consider
- Risk factors or red flags to watch for

Short, professional questions (max 50 chars each).

JSON format only:
{{"suggestions": ["question 1", "question 2"]}}"""
}


def generate_suggestions(user_message: str, assistant_response: str, language: str = "en") -> list:
    """
    Use Gemini 2.5 Flash to generate follow-up question suggestions.

    Args:
        user_message: The user's original question
        assistant_response: MedGemma's response
        language: Language code (uz, ru, en)

    Returns:
        List of 2 suggestion strings, or empty list if failed
    """
    if not GEMINI_API_KEY:
        logger.warning("⚠️ GEMINI_API_KEY not set, skipping suggestions")
        return []

    text = ""  # Initialize for error handling

    try:
        # Get the prompt template for the language
        prompt_template = SUGGESTION_PROMPTS.get(language, SUGGESTION_PROMPTS["en"])
        prompt = prompt_template.format(
            user_message=user_message[:500],  # Limit length
            assistant_response=assistant_response[:1500]  # Limit length
        )

        # Use Gemini 2.5 Flash
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

        headers = {
            "Content-Type": "application/json"
        }

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1024,
                "thinkingConfig": {
                    "thinkingBudget": 0
                }
            }
        }

        logger.info(f"🔄 Generating suggestions with Gemini 2.5 Flash (language: {language})...")

        response = requests.post(url, headers=headers, json=payload, timeout=60)

        if response.status_code != 200:
            logger.error(f"❌ Gemini API error: {response.status_code} - {response.text[:500]}")
            return []

        result = response.json()

        # Extract text from response - handle different response structures
        candidates = result.get("candidates", [])
        if not candidates:
            logger.error(f"❌ No candidates in Gemini response: {result}")
            return []

        candidate = candidates[0]
        content = candidate.get("content", {})
        parts = content.get("parts", [])

        if not parts:
            logger.error(f"❌ No parts in Gemini response. Candidate: {candidate}")
            return []

        # Log all parts to debug
        logger.info(f"📥 Gemini response has {len(parts)} parts")
        for i, part in enumerate(parts):
            part_keys = list(part.keys())
            logger.info(f"   Part {i}: keys={part_keys}")

        # Gemini 2.5 Flash returns multiple parts:
        # - Parts with "thought" key are thinking/reasoning (skip these)
        # - Parts with "text" key are actual response (use these)
        # Collect ALL text from non-thought parts
        all_text_parts = []
        for part in parts:
            # Skip thinking parts
            if "thought" in part:
                continue
            # Collect text parts
            if "text" in part:
                all_text_parts.append(part.get("text", ""))

        text = "\n".join(all_text_parts)
        logger.info(f"📝 Gemini combined text: {text}")

        if not text:
            logger.error("❌ Empty text in Gemini response")
            return []

        # Parse JSON from response
        # Clean up the text in case there's markdown formatting
        text = text.strip()

        # Remove markdown code blocks if present
        if "```" in text:
            # Extract content between ``` markers
            match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
            if match:
                text = match.group(1)

        text = text.strip()

        # Try to find JSON object in the text
        if not text.startswith("{"):
            start_idx = text.find("{")
            end_idx = text.rfind("}")
            if start_idx != -1 and end_idx != -1:
                text = text[start_idx:end_idx + 1]

        logger.info(f"📝 Cleaned JSON text: {text}")

        data = json.loads(text)
        suggestions = data.get("suggestions", [])

        # Ensure we have exactly 2 suggestions and they're not too long
        suggestions = [str(s)[:50] for s in suggestions[:2]]

        logger.info(f"✅ Generated {len(suggestions)} suggestions: {suggestions}")
        return suggestions

    except json.JSONDecodeError as e:
        logger.error(f"❌ Failed to parse Gemini response as JSON: {e}")
        logger.error(f"❌ Text was: {text[:500] if text else 'empty'}")
        return []
    except Exception as e:
        logger.error(f"❌ Error generating suggestions: {e}", exc_info=True)
        return []
