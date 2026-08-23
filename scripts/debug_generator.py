import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

import logging
logging.basicConfig(level=logging.INFO)

from backend.core.generator import get_generator

gen = get_generator()
response = gen.generate_response("Tell me about the ELSS Tax Saver fund.")
print("Response Dict:")
print(response)
