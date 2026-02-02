import requests
from google.auth import default
from google.auth.transport.requests import Request

from .config import (
    PROJECT_ID, LOCATION, ENDPOINT_ID, DEDICATED_ENDPOINT_DNS, logger
)
from .prompts import get_system_prompt


def _get_credentials():
    """Get and refresh Google Cloud credentials"""
    credentials, _ = default()
    if not credentials.valid:
        credentials.refresh(Request())
    return credentials


def _parse_response(result: dict) -> str:
    """Parse the MedGemma API response"""
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


def call_medgemma(
    user_message: str,
    language: str = "en",
    history: list = None,
    timeout: int = 120
) -> str:
    """
    Call MedGemma dedicated endpoint with language-specific system prompt.

    Args:
        user_message: The user's current message
        language: Language code (uz, ru, en)
        history: List of previous messages [{"role": "user/assistant", "content": "..."}]
        timeout: Request timeout in seconds

    Returns:
        The model's response text
    """
    credentials = _get_credentials()

    url = f"https://{DEDICATED_ENDPOINT_DNS}/v1/projects/{PROJECT_ID}/locations/{LOCATION}/endpoints/{ENDPOINT_ID}:predict"

    headers = {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json"
    }

    system_prompt = get_system_prompt(language)

    # Build messages list
    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation history if provided
    if history:
        messages.extend(history)

    # Add current user message
    messages.append({"role": "user", "content": user_message})

    payload = {
        "instances": [{
            "@requestFormat": "chatCompletions",
            "messages": messages
        }]
    }

    logger.info(f"🔄 Calling MedGemma (language: {language}, history: {len(history) if history else 0} messages)...")

    response = requests.post(url, headers=headers, json=payload, timeout=timeout)

    if response.status_code != 200:
        logger.error(f"❌ HTTP {response.status_code}: {response.text}")
        raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")

    result = response.json()
    return _parse_response(result)


def call_medgemma_with_image(
    image_base64: str,
    user_message: str = None,
    language: str = "en",
    history: list = None,
    timeout: int = 120
) -> str:
    """
    Call MedGemma dedicated endpoint with image and optional text.

    Args:
        image_base64: Base64 encoded image
        user_message: Optional text message/caption
        language: Language code (uz, ru, en)
        history: List of previous messages
        timeout: Request timeout in seconds

    Returns:
        The model's response text
    """
    credentials = _get_credentials()

    url = f"https://{DEDICATED_ENDPOINT_DNS}/v1/projects/{PROJECT_ID}/locations/{LOCATION}/endpoints/{ENDPOINT_ID}:predict"

    headers = {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json"
    }

    system_prompt = get_system_prompt(language)

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

    # Build messages list
    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation history if provided (text only from history)
    if history:
        messages.extend(history)

    # Add current user message with image
    messages.append({"role": "user", "content": user_content})

    payload = {
        "instances": [{
            "@requestFormat": "chatCompletions",
            "messages": messages
        }]
    }

    logger.info(f"🔄 Calling MedGemma with image (language: {language})...")

    response = requests.post(url, headers=headers, json=payload, timeout=timeout)

    if response.status_code != 200:
        logger.error(f"❌ HTTP {response.status_code}: {response.text}")
        raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")

    result = response.json()
    return _parse_response(result)
