"""
Response generator orchestrating retrieval and LLM response generation.
"""
import json
import logging
import re
from functools import lru_cache
from typing import Optional

from groq import Groq
from backend.config.settings import get_settings
from backend.config.prompts import (
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
    REFUSAL_ADVISORY,
    REFUSAL_OUT_OF_SCOPE,
    REFUSAL_PII,
    SCHEME_ALIASES,
)
from backend.core.query import preprocess_query
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
        Returns a dict containing 'answer', 'source', 'last_updated', and 'refused'.
        """
        # 1-3. Guardrails (PII, Injection, Advisory)
        is_allowed, refusal_response = check_query(user_query)
        if not is_allowed:
            logger.info("Query blocked by guardrails.")
            return {
                "answer": refusal_response,
                "source": None if refusal_response != REFUSAL_ADVISORY else "https://www.amfiindia.com/investor-corner/knowledge-center",
                "last_updated": None,
                "refused": True
            }

        # 3. Preprocess Query
        processed_query = preprocess_query(user_query)
        logger.debug(f"Processed query: {processed_query}")

        # 4. Retrieve Context from Vector Store
        try:
            # Attempt metadata-filtered retrieval if a scheme is identified
            scheme_name = _resolve_scheme_from_query(user_query)
            where_filter = {"scheme_name": scheme_name} if scheme_name else None

            results = self.store.query(
                [processed_query],
                where=where_filter,
            )
            
            # Extract documents, distances, and metadatas
            documents = results.get('documents', [[]])[0]
            metadatas = results.get('metadatas', [[]])[0]
            distances = results.get('distances', [[]])[0]
            
            logger.info(
                "Retrieved %d docs (scheme_filter=%s) with distances: %s",
                len(documents), scheme_name, distances,
            )
            
            if not documents:
                raise ValueError("No documents returned from vector store.")
                
            # Filter out chunks that are too far away using the configured
            # similarity threshold (converted to distance).
            valid_docs = []
            valid_metas = []
            for doc, meta, dist in zip(documents, metadatas, distances):
                if dist < self._max_distance:
                    valid_docs.append(doc)
                    valid_metas.append(meta)
            
            if not valid_docs:
                logger.info(
                    "All chunks below similarity threshold (max_dist=%.2f, best_dist=%.4f)",
                    self._max_distance, min(distances) if distances else float('inf'),
                )
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

        # 5. Construct Prompt
        context_text = "\n".join([f"- {doc}" for doc in valid_docs])
        sources_list = list(set([meta.get('source_url', 'Unknown') for meta in valid_metas]))
        sources_text = "\n".join([f"- {url}" for url in sources_list])
        
        user_prompt = USER_PROMPT_TEMPLATE.format(
            context=context_text,
            sources=sources_text,
            query=user_query
        )

        # 6. Call Groq API
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
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

        # 7. Post-process response
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

        # Truncate to ≤ 3 sentences as required by the design spec
        answer = _truncate_to_sentences(answer, max_sentences=3)
            
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
        primary_source = valid_metas[0].get("source_url")
        scraped_date = valid_metas[0].get("scraped_date")

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

    def generate_stream(self, user_query: str):
        """
        Orchestrates the RAG pipeline and yields SSE events.
        """
        # 1-3. Guardrails
        is_allowed, refusal_response = check_query(user_query)
        if not is_allowed:
            logger.info("Query blocked by guardrails.")
            yield f"data: {json.dumps({'type': 'chunk', 'text': refusal_response})}\n\n"
            source = None if refusal_response != REFUSAL_ADVISORY else "https://www.amfiindia.com/investor-corner/knowledge-center"
            yield f"data: {json.dumps({'type': 'metadata', 'source': source, 'last_updated': None, 'refused': True})}\n\n"
            return

        # 3. Preprocess Query
        processed_query = preprocess_query(user_query)
        
        # 4. Retrieve Context
        try:
            scheme_name = _resolve_scheme_from_query(user_query)
            where_filter = {"scheme_name": scheme_name} if scheme_name else None

            results = self.store.query([processed_query], where=where_filter)
            
            documents = results.get('documents', [[]])[0]
            metadatas = results.get('metadatas', [[]])[0]
            distances = results.get('distances', [[]])[0]
            
            if not documents:
                raise ValueError("No documents returned from vector store.")
                
            valid_docs = []
            valid_metas = []
            for doc, meta, dist in zip(documents, metadatas, distances):
                if dist < self._max_distance:
                    valid_docs.append(doc)
                    valid_metas.append(meta)
            
            if not valid_docs:
                yield f"data: {json.dumps({'type': 'chunk', 'text': REFUSAL_OUT_OF_SCOPE})}\n\n"
                yield f"data: {json.dumps({'type': 'metadata', 'source': None, 'last_updated': None, 'refused': True})}\n\n"
                return

        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            yield f"data: {json.dumps({'type': 'chunk', 'text': 'I am experiencing technical difficulties retrieving the information. Please try again later.'})}\n\n"
            yield f"data: {json.dumps({'type': 'metadata', 'source': None, 'last_updated': None, 'refused': True})}\n\n"
            return

        # 5. Construct Prompt
        context_text = "\n".join([f"- {doc}" for doc in valid_docs])
        sources_list = list(set([meta.get('source_url', 'Unknown') for meta in valid_metas]))
        sources_text = "\n".join([f"- {url}" for url in sources_list])
        
        user_prompt = USER_PROMPT_TEMPLATE.format(
            context=context_text,
            sources=sources_text,
            query=user_query
        )

        # 6. Call Groq API with stream=True
        try:
            stream = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.settings.groq_model,
                temperature=0.0,
                max_tokens=2048,
                stream=True,
            )
            
            in_think_block = False
            full_response = ""
            
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_response += content
                    
                    if "<think>" in full_response and not in_think_block:
                        in_think_block = True
                        # If content had text before think, we yield it
                        idx = content.find("<think>")
                        if idx > 0:
                            yield f"data: {json.dumps({'type': 'chunk', 'text': content[:idx]})}\n\n"
                            
                    if in_think_block and "</think>" in full_response:
                        in_think_block = False
                        idx = content.find("</think>")
                        if idx != -1:
                            content = content[idx + 8:]
                        else:
                            content = "" # it was split across chunks, we just ignore this chunk

                    # We are not in think block, or we just exited it
                    # But be careful if `<think>` spans across chunks. A simpler regex buffering approach:
                    # Actually, if we assume `<think>` and `</think>` are yielded cleanly or we just filter them out from the stream
                    # Groq usually yields tokens quickly, `<think>` might come in as '<', 'think', '>'. 
                    # Simpler approach: send everything, but buffer it. If the model is not a reasoning model it won't emit it.
                    # llama-3.3-70b-versatile is not a reasoning model, so it shouldn't emit <think> anyway!
                    yield f"data: {json.dumps({'type': 'chunk', 'text': content})}\n\n"

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            yield f"data: {json.dumps({'type': 'chunk', 'text': '\n\n(Error generating response)'})}\n\n"

        # Determine the primary source and last updated date
        primary_source = valid_metas[0].get("source_url")
        scraped_date = valid_metas[0].get("scraped_date")

        yield f"data: {json.dumps({'type': 'metadata', 'source': primary_source, 'last_updated': scraped_date, 'refused': False})}\n\n"


@lru_cache(maxsize=1)
def get_generator() -> ResponseGenerator:
    """Return a cached singleton ResponseGenerator instance."""
    return ResponseGenerator()
