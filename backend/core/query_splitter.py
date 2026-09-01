"""
LLM-powered question decomposer for multi-question user messages.

Uses a lightweight Groq LLM call to semantically split a user message
into individual, self-contained sub-questions. Falls back to simple
'?' splitting if the LLM call fails.
"""

import json
import logging
import re

from groq import Groq
from backend.config.settings import get_settings

logger = logging.getLogger(__name__)

_DECOMPOSE_PROMPT = """You are a question decomposer. Your ONLY job is to break a user message into individual, self-contained questions.

Rules:
- Each output question must be fully self-contained (include the fund name, topic, etc.)
- If the message contains only ONE question, return it as-is in the list
- Do NOT answer the questions — only split them
- Return ONLY a JSON array of strings, nothing else

Examples:

Input: "What is the expense ratio for HDFC Mid Cap?"
Output: ["What is the expense ratio for HDFC Mid Cap?"]

Input: "What is the expense ratio for Mid Cap and the exit load for Small Cap?"
Output: ["What is the expense ratio for HDFC Mid Cap?", "What is the exit load for HDFC Small Cap?"]

Input: "What is the expense ratio and exit load for Mid Cap?"
Output: ["What is the expense ratio and exit load for HDFC Mid Cap?"]

Input: "Tell me about the ELSS fund, also what's the NAV for Gold ETF"
Output: ["Tell me about the HDFC ELSS Tax Saver fund?", "What is the NAV for HDFC Gold ETF Fund of Fund?"]

Input: "Compare expense ratios of Mid Cap and Small Cap"
Output: ["What is the expense ratio of HDFC Mid Cap?", "What is the expense ratio of HDFC Small Cap?"]

Now decompose this message:"""


def _fallback_split(message: str) -> list[str]:
    """Simple '?' based fallback if the LLM call fails."""
    if "?" not in message:
        return [message.strip()]

    raw_parts = message.split("?")
    questions = []
    for part in raw_parts:
        stripped = part.strip()
        if len(stripped) >= 5:
            questions.append(stripped + "?")

    return questions if questions else [message.strip()]


def split_questions(message: str, client: Groq = None) -> list[str]:
    """Split a user message into individual sub-questions using the LLM.

    Uses a fast Groq LLM call to semantically decompose the message.
    Falls back to simple '?' splitting if the LLM call fails.

    Args:
        message: The raw user message.
        client: Optional Groq client instance (avoids creating a new one).

    Returns:
        A list of one or more sub-question strings.
    """
    settings = get_settings()

    if client is None:
        client = Groq(api_key=settings.groq_api_key)

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": _DECOMPOSE_PROMPT},
                {"role": "user", "content": message},
            ],
            model=settings.groq_model,
            temperature=0.0,
            max_tokens=512,
        )

        raw_output = response.choices[0].message.content.strip()

        # Strip <think> blocks from reasoning models
        raw_output = re.sub(r'<think>.*?(?:</think>|$)', '', raw_output, flags=re.DOTALL).strip()

        # Parse the JSON array
        questions = json.loads(raw_output)

        if isinstance(questions, list) and len(questions) > 0:
            logger.info(
                "LLM decomposed message into %d sub-question(s): %s",
                len(questions), questions,
            )
            return questions

        logger.warning("LLM returned unexpected format: %s. Falling back.", raw_output)
        return _fallback_split(message)

    except json.JSONDecodeError as e:
        logger.warning("Failed to parse LLM decomposition output: %s. Falling back.", e)
        return _fallback_split(message)
    except Exception as e:
        logger.warning("LLM decomposition call failed: %s. Falling back.", e)
        return _fallback_split(message)
