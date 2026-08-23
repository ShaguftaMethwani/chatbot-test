"""
Unit tests for the RAG response generator.
"""
import unittest
from unittest.mock import patch, MagicMock
from backend.core.generator import ResponseGenerator
from backend.config.prompts import (
    REFUSAL_ADVISORY,
    REFUSAL_OUT_OF_SCOPE,
    REFUSAL_PII,
)

class TestResponseGenerator(unittest.TestCase):
    
    @patch('backend.core.generator.Groq')
    @patch('backend.core.generator.get_store')
    @patch('backend.core.generator.get_settings')
    def setUp(self, mock_settings, mock_get_store, mock_groq):
        # Setup mocks
        self.mock_settings = MagicMock()
        self.mock_settings.groq_api_key = "test_key"
        self.mock_settings.groq_model = "test_model"
        self.mock_settings.similarity_threshold = 0.35
        mock_settings.return_value = self.mock_settings
        
        self.mock_store = MagicMock()
        mock_get_store.return_value = self.mock_store
        
        self.mock_groq_client = MagicMock()
        mock_groq.return_value = self.mock_groq_client
        
        self.generator = ResponseGenerator()

    def test_pii_refusal(self):
        response = self.generator.generate_response("What is the NAV for my PAN ABCDE1234F?")
        self.assertTrue(response["refused"])
        self.assertEqual(response["answer"], REFUSAL_PII)

    def test_advisory_refusal(self):
        response = self.generator.generate_response("Which is the best fund to invest in?")
        self.assertTrue(response["refused"])
        self.assertEqual(response["answer"], REFUSAL_ADVISORY)

    def test_out_of_scope_refusal_no_chunks(self):
        # Mock store to return far distance (no valid chunks)
        # With similarity_threshold=0.35, max_distance = 1.0 - 0.35 = 0.65
        # So a distance of 0.8 should be filtered out.
        self.mock_store.query.return_value = {
            'documents': [['doc1']],
            'metadatas': [[{'source_url': 'test', 'scraped_date': '2026'}]],
            'distances': [[0.8]]  # > 0.65 threshold → filtered out
        }
        response = self.generator.generate_response("What is the weather like?")
        self.assertTrue(response["refused"])
        self.assertEqual(response["answer"], REFUSAL_OUT_OF_SCOPE)

    def test_successful_generation(self):
        # Mock store to return good distance (well within threshold)
        self.mock_store.query.return_value = {
            'documents': [['HDFC Mid-Cap has 0.75% expense ratio.']],
            'metadatas': [[{'source_url': 'https://test', 'scraped_date': '2026'}]],
            'distances': [[0.2]]
        }
        # Mock LLM response
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "The expense ratio is 0.75%."
        self.mock_groq_client.chat.completions.create.return_value = mock_completion
        
        response = self.generator.generate_response("What is the expense ratio?")
        self.assertFalse(response["refused"])
        self.assertIn("0.75%", response["answer"])
        self.assertEqual(response["source"], "https://test")
        self.assertEqual(response["last_updated"], "2026")

    def test_llm_idk_fallback_exact_token(self):
        """Test that the exact NO_INFO_AVAILABLE token triggers out-of-scope."""
        self.mock_store.query.return_value = {
            'documents': [['Some chunk text.']],
            'metadatas': [[{'source_url': 'https://test', 'scraped_date': '2026'}]],
            'distances': [[0.2]]
        }
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "NO_INFO_AVAILABLE"
        self.mock_groq_client.chat.completions.create.return_value = mock_completion
        
        response = self.generator.generate_response("Who is the CEO?")
        self.assertTrue(response["refused"])
        self.assertEqual(response["answer"], REFUSAL_OUT_OF_SCOPE)

    def test_llm_idk_fallback_natural_language(self):
        """Test that natural-language 'I don't have that information' also triggers out-of-scope."""
        self.mock_store.query.return_value = {
            'documents': [['Some chunk text.']],
            'metadatas': [[{'source_url': 'https://test', 'scraped_date': '2026'}]],
            'distances': [[0.2]]
        }
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "I don't have that information."
        self.mock_groq_client.chat.completions.create.return_value = mock_completion
        
        response = self.generator.generate_response("Who is the CEO?")
        self.assertTrue(response["refused"])
        self.assertEqual(response["answer"], REFUSAL_OUT_OF_SCOPE)

    def test_response_truncated_to_3_sentences(self):
        """Test that LLM responses exceeding 3 sentences are truncated."""
        self.mock_store.query.return_value = {
            'documents': [['HDFC Mid-Cap expense ratio is 0.75%.']],
            'metadatas': [[{'source_url': 'https://test', 'scraped_date': '2026'}]],
            'distances': [[0.2]]
        }
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = (
            "Sentence one. Sentence two. Sentence three. "
            "Sentence four should be cut. Sentence five also."
        )
        self.mock_groq_client.chat.completions.create.return_value = mock_completion
        
        response = self.generator.generate_response("Tell me about this fund.")
        self.assertFalse(response["refused"])
        # Count sentences in the answer (footer is no longer in answer body)
        sentences = [s for s in response["answer"].split(". ") if s.strip()]
        self.assertLessEqual(len(sentences), 3)

    def test_advisory_new_patterns(self):
        """Test newly added advisory patterns: safe bet, too high, your pick."""
        test_cases = [
            "Is HDFC Mid Cap a safe bet?",
            "Is the expense ratio too high?",
            "HDFC Mid Cap or Small Cap — your pick?",
            "Rate this fund out of 10",
        ]
        for query in test_cases:
            response = self.generator.generate_response(query)
            self.assertTrue(
                response["refused"],
                f"Expected refusal for: '{query}'"
            )


if __name__ == '__main__':
    unittest.main()
