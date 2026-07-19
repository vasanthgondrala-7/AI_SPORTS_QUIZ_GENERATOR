import os
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ['MOCK_MODE'] = '1'
from importlib import reload
import src.config as config
reload(config)
from src.generator import compile_quiz_data
print('MOCK_MODE', config.MOCK_MODE)
try:
    quiz, ctx, raw = compile_quiz_data('Cricket', 'Easy', num_questions=1)
    print('SUCCESS', quiz)
    print('RAW', raw)
except Exception as e:
    import traceback
    traceback.print_exc()
