"""
AWS Bedrock client wrapper for Claude Sonnet 4.5 invocations.
Includes retry logic, detailed error logging, and robust JSON parsing.
"""

import os
import json
import time
import logging
import boto3
from botocore.config import Config
from typing import Optional

logger = logging.getLogger(__name__)

_client = None


def get_client():
    global _client
    if _client is None:
        region = os.environ.get("BEDROCK_REGION", "us-east-1")
        config = Config(
            read_timeout=600,       # 10 min — Claude 4.5 large outputs need this
            connect_timeout=10,
            retries={"max_attempts": 0},  # We handle retries ourselves
        )
        _client = boto3.client("bedrock-runtime", region_name=region, config=config)
    return _client


def invoke_claude(
    system_prompt: str,
    user_message: str,
    model_id: str = None,
    max_tokens: int = 8192,
    temperature: float = 0.3,
    stop_sequences: Optional[list] = None,
    retries: int = 2,
) -> str:
    """
    Invoke Claude via Bedrock Messages API with retry logic.
    Returns the text content of the response.
    """
    client = get_client()
    model = model_id or os.environ.get(
        "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    )

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}],
    }

    if stop_sequences:
        body["stop_sequences"] = stop_sequences

    last_error = None
    for attempt in range(retries + 1):
        try:
            logger.info(
                f"Bedrock invoke: model={model}, max_tokens={max_tokens}, "
                f"input_chars={len(system_prompt) + len(user_message)}, attempt={attempt + 1}"
            )

            response = client.invoke_model(
                modelId=model,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body),
            )

            result = json.loads(response["body"].read())

            # Check for stop reason
            stop_reason = result.get("stop_reason", "unknown")
            usage = result.get("usage", {})
            logger.info(
                f"Bedrock response: stop_reason={stop_reason}, "
                f"input_tokens={usage.get('input_tokens', 0)}, "
                f"output_tokens={usage.get('output_tokens', 0)}"
            )

            text_parts = []
            for block in result.get("content", []):
                if block.get("type") == "text":
                    text_parts.append(block["text"])

            output = "\n".join(text_parts)

            if not output.strip():
                logger.warning("Bedrock returned empty text content")
                if attempt < retries:
                    time.sleep(2 ** attempt)
                    continue
                raise ValueError("Bedrock returned empty response")

            return output

        except client.exceptions.ThrottlingException as e:
            last_error = e
            wait = 2 ** (attempt + 1)
            logger.warning(f"Bedrock throttled, waiting {wait}s: {e}")
            time.sleep(wait)

        except client.exceptions.ModelTimeoutException as e:
            last_error = e
            wait = 5
            logger.warning(f"Bedrock model timeout, waiting {wait}s: {e}")
            time.sleep(wait)

        except Exception as e:
            last_error = e
            error_str = str(e)
            logger.error(f"Bedrock invoke failed (attempt {attempt + 1}): {error_str}")

            # Don't retry on validation errors (wrong model ID, etc.)
            if "ValidationException" in error_str or "AccessDeniedException" in error_str:
                raise

            if attempt < retries:
                time.sleep(2 ** attempt)
            else:
                raise

    raise last_error


def invoke_claude_json(
    system_prompt: str,
    user_message: str,
    model_id: str = None,
    max_tokens: int = 12000,
    temperature: float = 0.2,
) -> dict:
    """
    Invoke Claude and parse the response as JSON.
    Handles markdown fences, partial JSON, and truncated responses.
    """
    raw = invoke_claude(
        system_prompt=system_prompt,
        user_message=user_message,
        model_id=model_id,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    # Strip markdown code fences using regex (handles ```json, ```JSON, ``` with newlines)
    import re
    cleaned = raw.strip()
    cleaned = re.sub(r'^```(?:json|JSON)?\s*\n?', '', cleaned)
    cleaned = re.sub(r'\n?```\s*$', '', cleaned)
    cleaned = cleaned.strip()

    # Try direct parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.warning(f"Direct JSON parse failed at pos {e.pos}: {e.msg}")

    # Extract outermost JSON object
    start = cleaned.find("{")
    if start < 0:
        logger.error(f"No JSON object found in response. First 500 chars: {cleaned[:500]}")
        raise ValueError("No JSON object found in Claude response")

    # Find matching closing brace by counting depth
    depth = 0
    in_string = False
    escape_next = False
    end = -1
    for i in range(start, len(cleaned)):
        c = cleaned[i]
        if escape_next:
            escape_next = False
            continue
        if c == '\\' and in_string:
            escape_next = True
            continue
        if c == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end > start:
        try:
            return json.loads(cleaned[start:end])
        except json.JSONDecodeError as e2:
            logger.warning(f"Balanced extraction failed: {e2}")

    # Response was likely truncated (hit max_tokens) — try to close open structures
    logger.warning(f"Attempting truncated JSON repair. Raw length: {len(raw)}, depth remaining: {depth}")
    partial = cleaned[start:] if start >= 0 else cleaned

    # Walk backwards to find the last complete key-value pair
    # Then close all open braces/brackets
    open_brackets = partial.count("[") - partial.count("]")
    open_braces = partial.count("{") - partial.count("}")

    # Trim to last complete value (before trailing comma or incomplete value)
    trimmed = partial.rstrip()
    # Remove trailing incomplete content: partial strings, keys without values
    trimmed = re.sub(r',\s*"[^"]*"?\s*:?\s*"?[^"]*$', '', trimmed)
    trimmed = re.sub(r',\s*$', '', trimmed)

    # Recount after trimming
    open_brackets = trimmed.count("[") - trimmed.count("]")
    open_braces = trimmed.count("{") - trimmed.count("}")

    fixed = trimmed + ("]" * max(0, open_brackets)) + ("}" * max(0, open_braces))
    try:
        result = json.loads(fixed)
        logger.info("Successfully repaired truncated JSON")
        return result
    except json.JSONDecodeError as e3:
        logger.error(f"JSON repair also failed: {e3}")

    logger.error(f"All JSON parse attempts failed. First 500: {raw[:500]}")
    logger.error(f"Last 500: {raw[-500:]}")
    raise ValueError(
        f"Claude did not return valid JSON. "
        f"Response length: {len(raw)} chars. "
        f"First 200 chars: {raw[:200]}"
    )
