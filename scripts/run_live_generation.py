import os
import sys
from importlib import reload

# Ensure imports resolve
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)

# Force real LLM path (MOCK_MODE=0) to simulate live behavior and capture fallback
os.environ['MOCK_MODE'] = '0'

import src.config as config
reload(config)
from src.generator import compile_quiz_data

try:
    parsed, context, raw = compile_quiz_data('Cricket', 'Medium', num_questions=2)
    print('=== Parsed quiz keys ===')
    print(list(parsed.keys()))
    print('\n=== First question ===')
    print(parsed['quiz'][0]['question'])
    print('\n=== First explanation ===')
    print(parsed['quiz'][0]['explanation'])
    print('\n=== Raw LLM response indicator ===')
    print(raw)
except Exception as e:
    print('Generation failed with exception:')
    print(e)
