import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

from backend.vectorstore.store import get_store
from backend.core.query import preprocess_query

store = get_store()
query = sys.argv[1] if len(sys.argv) > 1 else "Tell me about the ELSS Tax Saver fund."
processed = preprocess_query(query)

results = store.query([processed])
print("Processed query:", processed)
print("Distances:", results.get("distances"))
print("Documents:", results.get("documents"))
