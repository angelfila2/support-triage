"""Extract a JSON object from an LLM response."""

import json


def extract_json(raw_text: str) -> dict:
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise ValueError("Model returned an empty or non-text response.")

    text = raw_text.strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        pass
    else:
        if isinstance(result, dict):
            return result

        raise ValueError("Model output must be a JSON object.")

    # Extract JSON surrounded by Markdown fences or conversational text.
    decoder = json.JSONDecoder()

    for index, character in enumerate(text):
        if character != "{":
            continue

        try:
            result, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue

        if isinstance(result, dict):
            return result

    raise ValueError("No valid JSON object found in model output.")