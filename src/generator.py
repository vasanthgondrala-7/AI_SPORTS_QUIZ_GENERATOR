from src.database import query_historic_facts
from src.search import get_live_news_context
from src.llm_client import LLMClient
from src.utils import parse_json_safe, validate_quiz_structure
from src.config import MOCK_MODE

import json
import re
import logging

logger = logging.getLogger(__name__)


def _explanation_references_sources(explanation: str) -> bool:
    """
    Verify explanation references at least one retrieval source.
    """

    if not explanation:
        return False

    patterns = [
        r"Web Source\s*\d+",
        r"HISTORICAL FACTS",
        r"Historical Facts",
        r"Source",
        r"Retrieved",
    ]

    return any(
        re.search(pattern, explanation, re.IGNORECASE)
        for pattern in patterns
    )


def _build_system_prompt(context: str) -> str:
    return f"""
You are a Senior Sports Journalist and Quiz Creator.

You must ONLY use the supplied CONTEXT.

Never invent facts.

Never hallucinate.

If the context does not contain enough information,
generate fewer questions rather than inventing answers.

Return ONLY valid JSON.

DO NOT wrap JSON in markdown.

DO NOT use ```.

DO NOT explain anything outside the JSON.

Output format:

{{
    "quiz":[
        {{
            "question":"Question text",
            "options":[
                "Option A",
                "Option B",
                "Option C",
                "Option D"
            ],
            "answer":"A",
            "explanation":"HISTORICAL FACTS: ..."
        }}
    ]
}}

Rules:

1. Exactly four options.

2. Answer must be A/B/C/D.

3. Every explanation MUST reference:

- HISTORICAL FACTS

or

- Web Source 1

or

- Web Source 2

4. Never repeat questions.

5. Never fabricate statistics.

6. Difficulty should match the requested level.

CONTEXT

{context}
"""


def _build_user_prompt(
    sport: str,
    difficulty: str,
    num_questions: int,
) -> str:

    return f"""
Generate exactly {num_questions} multiple choice questions.

Sport:

{sport}

Difficulty:

{difficulty}

Requirements

- Four options

- Correct answer

- Explanation

- JSON ONLY

- No markdown

- No extra text
"""


def compile_quiz_data(
    sport: str,
    difficulty: str,
    num_questions: int = 4,
):

    logger.info("Generating quiz")

    db_query = (
        f"{sport} history championships "
        f"records winners rules facts"
    )

    db_matches = query_historic_facts(
        sport=sport,
        query_text=db_query,
    )

    db_context = (
        "\n".join(db_matches)
        if db_matches
        else "No historical data available."
    )

    web_context = (
        get_live_news_context(sport)
        if not MOCK_MODE
        else ""
    )

    unified_context = f"""
==============================
HISTORICAL FACTS
==============================

{db_context}

==============================
LIVE INTERNET NEWS
==============================

{web_context}
"""

    system_prompt = _build_system_prompt(unified_context)

    user_prompt = _build_user_prompt(
        sport,
        difficulty,
        num_questions,
    )

    client = LLMClient()

    last_error = None
    last_response = None
    last_text = None

    for attempt in range(3):

        logger.info(
            "LLM Attempt %s",
            attempt + 1,
        )

        raw_text, raw_response = client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
            max_tokens=6000,
        )

        last_text = raw_text
        last_response = raw_response

        logger.info("Raw LLM Response")

        logger.info(raw_text)

        try:

            parsed = parse_json_safe(raw_text)

            validate_quiz_structure(parsed)

            for question in parsed["quiz"]:

                explanation = question.get(
                    "explanation",
                    "",
                )

                if not _explanation_references_sources(
                    explanation
                ):

                    question[
                        "explanation"
                    ] += (
                        " (Citation missing — "
                        "please verify manually.)"
                    )

            return (
                parsed,
                unified_context,
                raw_response,
            )

        except Exception as exc:

            last_error = exc

            logger.exception(exc)

            user_prompt = f"""
Previous response was invalid.

Return STRICT JSON ONLY.

Do not include markdown.

Do not include explanations outside JSON.

Try again.

Original request:

{user_prompt}
"""
        continue

    # -------------------------------------------------------
    # If the LLM itself returned a mock response,
    # try to use it before creating our own fallback.
    # -------------------------------------------------------

    if (
        isinstance(last_response, dict)
        and last_response.get("mock")
    ):
        try:
            parsed = parse_json_safe(last_text)

            if (
                isinstance(parsed, dict)
                and parsed.get("quiz")
            ):
                logger.info(
                    "Using mock quiz returned by LLM."
                )

                return (
                    parsed,
                    unified_context,
                    last_response,
                )

        except Exception:
            logger.exception(
                "Unable to parse mock response."
            )

    # -------------------------------------------------------
    # Construct local fallback
    # -------------------------------------------------------

    logger.warning(
        "Generating local fallback quiz."
    )

    fallback_quiz = {
        "quiz": []
    }

    historical_lines = [
        line.strip()
        for line in db_context.split("\n")
        if line.strip()
    ]

    if not historical_lines:
        historical_lines = [
            "Historical sports records unavailable."
        ]

    for index in range(num_questions):

        context_line = historical_lines[
            index % len(historical_lines)
        ]

        fallback_quiz["quiz"].append(
            {
                "question":
                    f"{sport}: Practice Question {index + 1}",

                "options": [
                    "Option A",
                    "Option B",
                    "Option C",
                    "Option D",
                ],

                "answer": "A",

                "explanation":
                    f"HISTORICAL FACTS: {context_line}. "
                    "This question was locally generated "
                    "because the LLM response could not "
                    "be validated."
            }
        )

    fallback_response = {
        "mock": True,
        "fallback": "constructed",
        "provider": "local",
        "error": str(last_error),
    }

    logger.warning(
        "Returning constructed fallback quiz."
    )

    return (
        fallback_quiz,
        unified_context,
        fallback_response,
    )