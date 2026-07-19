from src.utils import parse_json_safe, QUIZ_SCHEMA
import json


def test_parse_json_safe_simple():
    text = '{"quiz": [{"question":"Q","options":["A","B","C","D"],"answer":"A","explanation":"e"}]}'
    data = parse_json_safe(text)
    assert data["quiz"][0]["question"] == "Q"
