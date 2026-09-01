"""
Response generator orchestrating retrieval and LLM response generation.
"""
import logging
import re
from functools import lru_cache
from typing import Optional

from groq import Groq
from backend.config.settings import get_settings
from backend.config.prompts import (
    SYSTEM_PROMPT_TEMPLATE,
    USER_PROMPT_TEMPLATE,
    REFUSAL_ADVISORY,
    REFUSAL_OUT_OF_SCOPE,
    REFUSAL_PII,
    SCHEME_ALIASES,
)
from backend.core.query import preprocess_query
from backend.core.query_splitter import split_questions
from backend.core.guardrails import check_query
from backend.vectorstore.store import get_store

logger = logging.getLogger(__name__)

# Patterns that indicate the LLM could not find the answer in context
_NO_INFO_PATTERNS = [
    r"no_info_available",
    r"i don'?t have that information",
    r"i do not have that information",
    r"information is not available",
    r"not (?:found|available|provided) in (?:the |my )?(?:context|data|knowledge)",
]


def _truncate_to_sentences(text: str, max_sentences: int = 3) -> str:
    """Truncate text to at most `max_sentences` sentences."""
    # Split on sentence-ending punctuation followed by whitespace
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    if len(sentences) <= max_sentences:
        return text.strip()
    truncated = " ".join(sentences[:max_sentences])
    logger.warning(
        "LLM response exceeded %d sentences (%d found); truncated.",
        max_sentences, len(sentences),
    )
    return truncated


def _strip_ai_disclaimers(text: str) -> str:
    """Remove common AI self-referential disclaimers from LLM output."""
    disclaimer_patterns = [
        r"(?:^|\n)\s*(?:As an AI|I'?m (?:just )?an? (?:AI|language model|assistant)).*?[.!]\s*",
        r"(?:^|\n)\s*(?:Please note that I|Note:|Disclaimer:).*?[.!]\s*",
    ]
    for pattern in disclaimer_patterns:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE).strip()
    return text


def _resolve_scheme_from_query(query: str) -> Optional[str]:
    """Try to resolve a canonical scheme name from the query text."""
    lower = query.lower()
    for alias, canonical in SCHEME_ALIASES.items():
        if alias in lower or canonical.lower() in lower:
            return canonical
    return None


class ResponseGenerator:
    def __init__(self):
        self.settings = get_settings()
        self.client = Groq(api_key=self.settings.groq_api_key)
        self.store = get_store()
        # Convert similarity threshold to cosine distance threshold
        # ChromaDB cosine distance = 1 - cosine_similarity
        self._max_distance = 1.0 - self.settings.similarity_threshold

    def generate_response(self, user_query: str) -> dict:
        """
        Orchestrates the entire RAG pipeline for a given user query.
        Supports multiple questions in a single message.
        Returns a dict containing 'answer', 'source', 'last_updated', and 'refused'.
        """
        # 1. Guardrails (PII, Injection, Advisory)
        is_allowed, refusal_response = check_query(user_query)
        if not is_allowed:
            logger.info("Query blocked by guardrails.")
            return {
                "answer": refusal_response,
                "source": None if refusal_response != REFUSAL_ADVISORY else "https://www.amfiindia.com/investor-corner/knowledge-center",
                "last_updated": None,
                "refused": True
            }

        # 2. Split into sub-questions using LLM decomposition
        sub_questions = split_questions(user_query, client=self.client)
        num_questions = len(sub_questions)
        logger.info("Processing %d sub-question(s)", num_questions)

        # 3. Retrieve context for each sub-question independently
        all_valid_docs = []
        all_valid_metas = []
        seen_docs = set()  # Deduplicate by document text

        try:
            for sq in sub_questions:
                processed_query = preprocess_query(sq)
                logger.debug("Processed sub-query: %s", processed_query)

                scheme_name = _resolve_scheme_from_query(sq)
                where_filter = {"scheme_name": scheme_name} if scheme_name else None

                results = self.store.query(
                    [processed_query],
                    where=where_filter,
                )

                documents = results.get('documents', [[]])[0]
                metadatas = results.get('metadatas', [[]])[0]
                distances = results.get('distances', [[]])[0]

                logger.info(
                    "Sub-query '%s': retrieved %d docs (scheme_filter=%s) with distances: %s",
                    sq[:50], len(documents), scheme_name, distances,
                )

                for doc, meta, dist in zip(documents, metadatas, distances):
                    if dist < self._max_distance and doc not in seen_docs:
                        all_valid_docs.append(doc)
                        all_valid_metas.append(meta)
                        seen_docs.add(doc)

            if not all_valid_docs:
                logger.info("No valid chunks found for any sub-question.")
                return {
                    "answer": REFUSAL_OUT_OF_SCOPE,
                    "source": None,
                    "last_updated": None,
                    "refused": True
                }

        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return {
                "answer": "I'm experiencing technical difficulties retrieving the information. Please try again later.",
                "source": None,
                "last_updated": None,
                "refused": True
            }

        # 4. Construct Prompt with merged context
        context_text = "\n".join([f"- {doc}" for doc in all_valid_docs])
        sources_list = list(set([meta.get('source_url', 'Unknown') for meta in all_valid_metas]))
        sources_text = "\n".join([f"- {url}" for url in sources_list])

        user_prompt = USER_PROMPT_TEMPLATE.format(
            context=context_text,
            sources=sources_text,
            query=user_query
        )

        # Dynamic sentence limit: 3 sentences per sub-question
        max_sentences = 3 * num_questions
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(max_sentences=max_sentences)

        # 5. Call Groq API
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.settings.groq_model,
                temperature=0.0,  # low temperature for factual answers
                max_tokens=2048,
            )
            answer = chat_completion.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return {
                "answer": "I'm experiencing technical difficulties generating a response. Please try again later.",
                "source": None,
                "last_updated": None,
                "refused": True
            }

        # 6. Post-process response
        raw_answer = answer
        logger.info(f"RAW LLM OUTPUT: {raw_answer}")

        # Strip <think> blocks that reasoning models might generate, even if unclosed
        clean_answer = re.sub(r'<think>.*?(?:</think>|$)', '', answer, flags=re.DOTALL).strip()

        # If the think block consumed all tokens and left no answer, use a fallback
        if not clean_answer:
            clean_answer = "I apologize, but I couldn't complete my response. Please try again."

        answer = clean_answer

        # Strip common AI disclaimers
        answer = _strip_ai_disclaimers(answer)

        # Truncate using the dynamic sentence limit
        answer = _truncate_to_sentences(answer, max_sentences=max_sentences)

        # If the LLM indicates it doesn't know, convert to out-of-scope refusal
        answer_lower = answer.lower()
        for pattern in _NO_INFO_PATTERNS:
            if re.search(pattern, answer_lower):
                return {
                    "answer": REFUSAL_OUT_OF_SCOPE,
                    "source": None,
                    "last_updated": None,
                    "refused": True
                }

        # Determine the primary source and last updated date from the first valid chunk
        primary_source = all_valid_metas[0].get("source_url")
        scraped_date = all_valid_metas[0].get("scraped_date")

        # Note: we do NOT append a "Last updated" footer to the answer text.
        # The frontend renders source and last_updated as separate structured
        # UI elements (badge + link), so embedding them in the answer body
        # would cause duplication.

        return {
            "answer": answer,
            "source": primary_source,
            "last_updated": scraped_date,
            "refused": False
        }


@lru_cache(maxsize=1)
def get_generator() -> ResponseGenerator:
    """Return a cached singleton ResponseGenerator instance."""
    return ResponseGenerator()
