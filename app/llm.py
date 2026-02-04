# Gemini 2.5 Flash LLM for medical chat
import requests
from .config import GEMINI_API_KEY, logger
from .prompts import get_system_prompt


def call_gemini(message: str, language: str = "en", history: list = None) -> str:
    """
    Call Gemini 2.5 Flash API for medical chat.

    Args:
        message: User's message
        language: Language code (uz, ru, en)
        history: List of previous messages [{"role": "user/assistant", "content": "..."}]

    Returns:
        Response text from Gemini
    """
    if not GEMINI_API_KEY:
        logger.error("❌ GEMINI_API_KEY not set")
        return "Error: API key not configured"

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

        # Get system prompt for the language
        system_prompt = get_system_prompt(language)

        # Build conversation contents
        contents = []

        # Add conversation history
        if history:
            for msg in history:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg["content"]}]
                })

        # Add current message
        contents.append({
            "role": "user",
            "parts": [{"text": message}]
        })

        payload = {
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 4096,
                "thinkingConfig": {
                    "thinkingBudget": 0
                }
            }
        }

        logger.info(f"🔄 Calling Gemini 2.5 Flash (lang: {language}, history: {len(history) if history else 0} msgs)...")

        response = requests.post(url, json=payload, timeout=120)

        if response.status_code != 200:
            logger.error(f"❌ Gemini API error: {response.status_code} - {response.text[:500]}")
            return f"Error: API returned {response.status_code}"

        result = response.json()
        candidates = result.get("candidates", [])

        if not candidates:
            logger.error(f"❌ No candidates in response: {result}")
            return "Error: No response from model"

        parts = candidates[0].get("content", {}).get("parts", [])

        # Collect text parts (skip thinking parts)
        text_parts = []
        for part in parts:
            if "thought" in part:
                continue
            if "text" in part:
                text_parts.append(part.get("text", ""))

        response_text = "\n".join(text_parts).strip()

        if not response_text:
            logger.error("❌ Empty response from Gemini")
            return "Error: Empty response from model"

        logger.info(f"✅ Gemini response received ({len(response_text)} chars)")
        return response_text

    except requests.exceptions.Timeout:
        logger.error("❌ Gemini API timeout")
        return "Error: Request timeout"
    except Exception as e:
        logger.error(f"❌ Gemini error: {e}", exc_info=True)
        return f"Error: {str(e)}"


def call_gemini_with_image(image_base64: str, caption: str = "", language: str = "en", history: list = None) -> str:
    """
    Call Gemini 2.5 Flash API with an image for medical image analysis.

    Args:
        image_base64: Base64 encoded image
        caption: Optional caption/question about the image
        language: Language code (uz, ru, en)
        history: List of previous messages

    Returns:
        Response text from Gemini
    """
    if not GEMINI_API_KEY:
        logger.error("❌ GEMINI_API_KEY not set")
        return "Error: API key not configured"

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

        # Get system prompt for the language
        system_prompt = get_system_prompt(language)

        # Build conversation contents
        contents = []

        # Add conversation history (text only)
        if history:
            for msg in history:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg["content"]}]
                })

        # Build the image message
        image_prompt = caption if caption else "Please analyze this medical image and provide clinical insights."

        contents.append({
            "role": "user",
            "parts": [
                {"text": image_prompt},
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": image_base64
                    }
                }
            ]
        })

        payload = {
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 4096,
                "thinkingConfig": {
                    "thinkingBudget": 0
                }
            }
        }

        logger.info(f"🔄 Calling Gemini 2.5 Flash with image (lang: {language})...")

        response = requests.post(url, json=payload, timeout=120)

        if response.status_code != 200:
            logger.error(f"❌ Gemini API error: {response.status_code} - {response.text[:500]}")
            return f"Error: API returned {response.status_code}"

        result = response.json()
        candidates = result.get("candidates", [])

        if not candidates:
            logger.error(f"❌ No candidates in response: {result}")
            return "Error: No response from model"

        parts = candidates[0].get("content", {}).get("parts", [])

        # Collect text parts (skip thinking parts)
        text_parts = []
        for part in parts:
            if "thought" in part:
                continue
            if "text" in part:
                text_parts.append(part.get("text", ""))

        response_text = "\n".join(text_parts).strip()

        if not response_text:
            logger.error("❌ Empty response from Gemini")
            return "Error: Empty response from model"

        logger.info(f"✅ Gemini image response received ({len(response_text)} chars)")
        return response_text

    except requests.exceptions.Timeout:
        logger.error("❌ Gemini API timeout")
        return "Error: Request timeout"
    except Exception as e:
        logger.error(f"❌ Gemini error: {e}", exc_info=True)
        return f"Error: {str(e)}"
