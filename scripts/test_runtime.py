import os
import sys
from importlib import reload

# Ensure project root on sys.path so `src` package imports resolve
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)

os.environ['MOCK_MODE'] = '1'
# Ensure the config module reads the env var freshly
import src.config as config
reload(config)
from importlib import reload as _reload
import os

os.environ['MOCK_MODE'] = '1'
import src.config as config
_reload(config)

from src.generator import compile_quiz_data

parsed, context, raw = compile_quiz_data('Cricket', 'Easy', num_questions=2)
print('Parsed keys:', list(parsed.keys()))
print('First question:', parsed['quiz'][0]['question'])
print('First explanation:', parsed['quiz'][0]['explanation'])
print('Raw response indicator:', raw)
