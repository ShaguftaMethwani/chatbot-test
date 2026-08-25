"""
Prompt templates and static data for the RAG response generator.
"""

SYSTEM_PROMPT = """You are a facts-only mutual fund assistant. You answer questions
about HDFC mutual fund schemes using ONLY the provided context.

Rules:
- Maximum 3 sentences in your response
- Include exactly one source citation from the context metadata
- Never provide investment advice, opinions, or recommendations
- If the context does not contain the answer, say exactly "NO_INFO_AVAILABLE"
- Never fabricate or estimate data
- Be precise with numbers (expense ratios, amounts, percentages)
"""

USER_PROMPT_TEMPLATE = """Context:
{context}

Source URLs:
{sources}

Question: {query}

Provide a factual answer based solely on the context above."""

REFUSAL_ADVISORY = """I'm a facts-only assistant and cannot provide investment advice
or recommendations. For investment guidance, please consult a SEBI-registered
financial advisor.

Learn more: https://www.amfiindia.com/investor-corner/knowledge-center"""

REFUSAL_OUT_OF_SCOPE = """I can only answer factual questions about general mutual fund concepts (like taxation, NAV, CAS, and statements) and the following HDFC mutual fund schemes: Mid-Cap Opportunities, Small Cap, Gold ETF Fund of Fund, Top 100 (Large Cap), and ELSS Tax Saver. Please try a question within this scope."""

REFUSAL_PII = """For your security, I cannot process messages containing personal
information like PAN, Aadhaar, phone numbers, or email addresses. Please remove
any personal details and try again."""

SCHEME_ALIASES = {
    "hdfc midcap": "HDFC Mid-Cap Opportunities Fund",
    "hdfc mid cap": "HDFC Mid-Cap Opportunities Fund",
    "midcap opportunities": "HDFC Mid-Cap Opportunities Fund",
    "hdfc small cap": "HDFC Small Cap Fund",
    "hdfc smallcap": "HDFC Small Cap Fund",
    "hdfc gold": "HDFC Gold ETF Fund of Fund",
    "gold etf": "HDFC Gold ETF Fund of Fund",
    "hdfc large cap": "HDFC Top 100 Fund",
    "hdfc top 100": "HDFC Top 100 Fund",
    "hdfc largecap": "HDFC Top 100 Fund",
    "hdfc elss": "HDFC ELSS Tax Saver Fund",
    "elss tax saver": "HDFC ELSS Tax Saver Fund",
    "hdfc tax saver": "HDFC ELSS Tax Saver Fund",
}
