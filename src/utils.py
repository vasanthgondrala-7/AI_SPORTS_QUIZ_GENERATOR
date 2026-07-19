import json
import re
from typing import Any
from jsonschema import validate, ValidationError


QUIZ_SCHEMA = {
    "type": "object",
    "properties": {
        "quiz": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "options": {
                        "type": "array",
                        "minItems": 4,
                        "maxItems": 4
                    },
                    "answer": {
                        "type": "string",
                        "pattern": "^[A-D]$"
                    },
                    "explanation": {
                        "type": "string"
                    },
                },
                "required": [
                    "question",
                    "options",
                    "answer",
                    "explanation",
                ],
            },
        }
    },
    "required": ["quiz"],
}


def parse_json_safe(text: str) -> Any:
    """
    Parse JSON returned by Gemini/OpenAI.

    Handles:
    - Raw JSON
    - ```json ... ```
    - ``` ... ```
    - Extra explanatory text
    - Leading/trailing whitespace
    """

    if not text:
        raise ValueError("Empty LLM response")

    text = text.strip()

    # Try direct JSON first
    try:
        return json.loads(text)
    except Exception:
        pass

    # Remove Markdown code fences
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    # Try again
    try:
        return json.loads(text)
    except Exception:
        pass

    # Extract JSON object
    match = re.search(r"\{[\s\S]*\}", text)

    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass

    # Extract JSON array
    match = re.search(r"\[[\s\S]*\]", text)

    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass

    print("=" * 80)
    print("FAILED TO PARSE JSON")
    print(text)
    print("=" * 80)

    raise ValueError("Unable to parse JSON from LLM output")


def validate_quiz_structure(doc: Any) -> None:
    try:
        validate(instance=doc, schema=QUIZ_SCHEMA)
    except ValidationError as e:
        raise ValueError(f"Quiz validation failed: {e.message}")