import json
import re
import time
from typing import Tuple

import requests
from openai import OpenAI

from src.config import (
    OPENAI_API_KEY,
    GEMINI_API_KEY,
    LLM_PROVIDER,
    MOCK_MODE,
    GEMINI_MODEL,
)


class LLMClient:
    def __init__(self, api_key: str = None):
        self.provider = (LLM_PROVIDER or "openai").strip().lower()

        if self.provider == "gemini":
            self.api_key = api_key or GEMINI_API_KEY
        else:
            self.api_key = api_key or OPENAI_API_KEY

        self.use_live = bool(self.api_key and not MOCK_MODE)

        self.client = (
            OpenAI(api_key=self.api_key)
            if self.provider == "openai" and self.use_live
            else None
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _mock_response(self, reason: str = ""):
        mock = {
            "quiz": [
                {
                    "question": "Which country won the Thomas Cup in 2022?",
                    "options": [
                        "Indonesia",
                        "India",
                        "China",
                        "Denmark",
                    ],
                    "answer": "B",
                    "explanation": (
                        "HISTORICAL FACTS: India won its first-ever Thomas Cup "
                        "title in 2022 by defeating Indonesia."
                        + (f" ({reason})" if reason else "")
                    ),
                },
                {
                    "question": "Where was the first official Test cricket match played in 1877?",
                    "options": [
                        "Lord's",
                        "Eden Gardens",
                        "Melbourne Cricket Ground",
                        "SCG",
                    ],
                    "answer": "C",
                    "explanation": (
                        "HISTORICAL FACTS: The first official Test match was "
                        "played at the Melbourne Cricket Ground in 1877."
                        + (f" ({reason})" if reason else "")
                    ),
                },
            ]
        }

        raw = {
            "mock": True,
            "reason": reason,
            "mock_context": [
                "HISTORICAL FACTS: Thomas Cup records",
                "Web Source 1: Mock sports article",
            ],
        }

        return json.dumps(mock, ensure_ascii=False, indent=2), raw

    def _strip_markdown(self, text: str) -> str:
        """
        Remove markdown fences and return only JSON.
        """

        if not text:
            return text

        text = text.strip()

        # Remove ```json ... ```
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE | re.MULTILINE)
        text = re.sub(r"```$", "", text, flags=re.MULTILINE)

        text = text.strip()

        # Extract JSON object if surrounded by text
        first = text.find("{")
        last = text.rfind("}")

        if first != -1 and last != -1 and last > first:
            text = text[first:last + 1]

        return text.strip()

    # ------------------------------------------------------------------
    # Main API
    # ------------------------------------------------------------------

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 800,
    ) -> Tuple[str, dict]:
        """
        Call the configured LLM and return:

            (response_text, raw_response)

        response_text is always cleaned so downstream JSON parsing
        receives only valid JSON text.
        """

        if not self.use_live:
            return self._mock_response()

        # ==============================================================
        # OPENAI
        # ==============================================================

        if self.provider == "openai":

            last_exception = None

            for attempt in range(5):
                try:
                    response = self.client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    system_prompt
                                    + "\n\n"
                                    + "IMPORTANT:\n"
                                    + "- Return ONLY valid JSON.\n"
                                    + "- Do NOT use markdown.\n"
                                    + "- Do NOT wrap JSON inside ``` blocks.\n"
                                ),
                            },
                            {
                                "role": "user",
                                "content": user_prompt,
                            },
                        ],
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )

                    text = response.choices[0].message.content or ""
                    text = self._strip_markdown(text)

                    return text, response

                except Exception as exc:
                    last_exception = exc
                    error = str(exc).lower()

                    if (
                        "quota" in error
                        or "429" in error
                        or "insufficient_quota" in error
                    ):
                        return self._mock_response(
                            "Fallback mock due to OpenAI quota"
                        )

                    if attempt < 4:
                        time.sleep(2 ** attempt)
                        continue

            raise RuntimeError(
                f"OpenAI request failed after retries: {last_exception}"
            )

        # ==============================================================
        # GEMINI
        # ==============================================================

        if self.provider == "gemini":

            model = GEMINI_MODEL or "gemini-2.5-flash"

            endpoint = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model}:generateContent"
            )

            params = {
                "key": self.api_key,
            }

            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": (
                                    system_prompt
                                    + "\n\n"
                                    + "IMPORTANT:\n"
                                    + "- Return ONLY valid JSON.\n"
                                    + "- No markdown.\n"
                                    + "- No explanations.\n"
                                    + "- No ```json fences.\n\n"
                                    + user_prompt
                                )
                            }
                        ],
                    }
                ],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                    "responseMimeType": "application/json",
                },
            }

            last_exception = None

            for attempt in range(5):
                try:
                    response = requests.post(
                        endpoint,
                        params=params,
                        json=payload,
                        timeout=60,
                    )

                    if response.status_code != 200:
                        raise RuntimeError(
                            f"Gemini API returned {response.status_code}: {response.text}"
                        )

                    body = response.json()

                    candidate = body["candidates"][0]

                    finish_reason = candidate.get("finishReason")

                    print("Finish reason:", finish_reason)

                    if finish_reason == "MAX_TOKENS":
                        if attempt < 4:
                            max_tokens = min(max_tokens * 2, 8192)
                            time.sleep(2 ** attempt)
                            continue

                    candidates = body.get("candidates", [])

                    if not candidates:
                        raise RuntimeError(
                            f"No candidates returned by Gemini.\n{body}"
                        )

                    parts = (
                        candidates[0]
                        .get("content", {})
                        .get("parts", [])
                    )

                    if not parts:
                        raise RuntimeError(
                            f"No content parts returned by Gemini.\n{body}"
                        )

                    text = parts[0].get("text", "")

                    if not text:
                        raise RuntimeError(
                            f"Empty Gemini response.\n{body}"
                        )

                    text = self._strip_markdown(text)

                    return text, body

                except Exception as exc:
                    last_exception = exc
                    error = str(exc).lower()

                    if (
                        "quota" in error
                        or "429" in error
                        or "resource_exhausted" in error
                        or "insufficient_quota" in error
                    ):
                        return self._mock_response(
                            "Fallback mock due to Gemini quota"
                        )

                    if attempt < 4:
                        time.sleep(2 ** attempt)
                        continue

            raise RuntimeError(
                f"Gemini request failed after retries: {last_exception}"
            )

        raise ValueError(f"Unsupported LLM provider: {self.provider}")