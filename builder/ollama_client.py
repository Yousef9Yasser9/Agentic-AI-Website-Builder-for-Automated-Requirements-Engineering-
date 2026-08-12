import json
import re
import time
from typing import Any, Dict, Optional

import requests

OLLAMA_BASE_URL = "http://127.0.0.1:11434"
OLLAMA_CHAT_URL = f"{OLLAMA_BASE_URL}/api/chat"
OLLAMA_GENERATE_URL = f"{OLLAMA_BASE_URL}/api/generate"


def _generate_prompt(system: str, user: str) -> str:
    return (
        "System:\n"
        f"{system.strip()}\n\n"
        "User:\n"
        f"{user.strip()}\n\n"
        "Assistant:\n"
    )


def ollama_chat(
    model: str,
    system: str,
    user: str,
    temperature: float = 0.2,
    timeout_sec: int = 900,
    retries: int = 4,
    num_predict: int = 1200,
    num_ctx: int = 2048,
    num_gpu: int = -1,
    response_format: Optional[str] = None, # NEW: Allow generic text or forced JSON
) -> str:
    chat_payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
            "num_ctx": num_ctx,
            "num_gpu": num_gpu,
        },
        "stream": False,
    }
    if response_format:
        chat_payload["format"] = response_format

    generate_payload = {
        "model": model,
        "system": system,
        "prompt": _generate_prompt(system, user),
        "options": chat_payload["options"],
        "stream": False,
    }
    if response_format:
        generate_payload["format"] = response_format

    last_err = None
    for attempt in range(retries + 1):
        try:
            r = requests.post(OLLAMA_CHAT_URL, json=chat_payload, timeout=timeout_sec)
            if r.status_code == 404:
                r = requests.post(OLLAMA_GENERATE_URL, json=generate_payload, timeout=timeout_sec)
            r.raise_for_status()
            data = r.json()
            if "message" in data:
                return (data.get("message", {}) or {}).get("content", "") or ""
            return data.get("response", "") or ""
        except requests.exceptions.ConnectionError as e:
            last_err = e
            if attempt < retries:
                wait = 3.0 * (attempt + 1)
                time.sleep(wait)
                continue
            raise ConnectionError(
                "Cannot connect to Ollama at http://127.0.0.1:11434. "
                "Start Ollama from the system tray or run `ollama serve`, then retry."
            ) from e
        except requests.exceptions.Timeout as e:
            last_err = e
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise TimeoutError(
                f"Ollama did not finish within {timeout_sec} seconds. "
                "The request was stopped instead of waiting indefinitely."
            ) from e
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise last_err


def _strip_fences(text: str) -> str:
    """Remove markdown code fences and surrounding text."""
    if not text:
        return ""
    
    t = text.strip()
    
    # Remove opening fence with optional language specifier
    t = re.sub(r"^```(?:json|python|html|javascript|typescript)?\s*\n?", "", t, flags=re.IGNORECASE)
    # Remove closing fence
    t = re.sub(r"\n?\s*```$", "", t)
    
    return t.strip()


def _find_balanced_json(text: str) -> Optional[str]:
    """
    Find the first balanced JSON object or array in text.
    Handles nested structures properly.
    """
    if not text:
        return None
    
    # Find first { or [
    start_idx = -1
    for i, ch in enumerate(text):
        if ch in ('{', '['):
            start_idx = i
            break
    
    if start_idx == -1:
        return None
    
    # Find matching closing bracket
    open_char = text[start_idx]
    close_char = '}' if open_char == '{' else ']'
    depth = 0
    in_string = False
    escape_next = False
    
    for i in range(start_idx, len(text)):
        ch = text[i]
        
        if escape_next:
            escape_next = False
            continue
        
        if ch == '\\':
            escape_next = True
            continue
        
        if ch == '"':
            in_string = not in_string
            continue
        
        if in_string:
            continue
        
        if ch == open_char:
            depth += 1
        elif ch == close_char:
            depth -= 1
            if depth == 0:
                return text[start_idx:i+1]
    
    # If we get here, brackets are unbalanced - return what we have
    return None


def _extract_json_block(text: str) -> Optional[str]:
    """
    Extract first JSON object/array inside a mixed response.
    More robust than regex - uses bracket matching.
    """
    if not text:
        return None

    # First try stripping fences
    t = _strip_fences(text)

    # If it starts with { or [, try to parse directly
    if t.startswith("{") or t.startswith("["):
        result = _find_balanced_json(t)
        if result:
            return result

    # Otherwise search for JSON in the text
    result = _find_balanced_json(text)
    if result:
        return result
    
    return None


def parse_json_with_fix(
    model: str,
    raw: str,
    timeout_sec: Optional[int] = 900,
    require_keys: Optional[list] = None,
    repair_retries: int = 1,
    repair_num_predict: int = 2000,
) -> Dict[str, Any]:
    """
    Robust JSON parsing with multiple fallback strategies:
    1. Direct parse
    2. Extract JSON from mixed text (with bracket matching)
    3. Ask LLM to repair
    4. Return partial result if keys are present
    """
    if raw is None or str(raw).strip() == "":
        raise ValueError(
            "Model returned EMPTY output. Likely timeout / overload / huge prompt. "
            "Try again, reduce payload size, or increase timeout."
        )

    def _has_keys(d: Any) -> bool:
        if not require_keys:
            return True
        if not isinstance(d, dict):
            return False
        return all(k in d for k in require_keys)

    # Strategy 1: Direct parse
    try:
        parsed = json.loads(raw)
        if _has_keys(parsed):
            return parsed
        # If keys missing but we got a dict, continue to try other strategies
        if isinstance(parsed, dict):
            pass  # Will try extraction next
    except Exception:
        pass

    # Strategy 2: Extract JSON from mixed text
    extracted = _extract_json_block(raw)
    if extracted:
        try:
            parsed = json.loads(extracted)
            if _has_keys(parsed):
                return parsed
            # If we got a valid dict but missing keys, still return it
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

    # Strategy 3: Try parsing with more aggressive cleaning
    cleaned = raw.strip()
    # Remove any leading/trailing non-JSON text
    cleaned = re.sub(r'^[^{\[]*', '', cleaned)
    cleaned = re.sub(r'[^}\]]*$', '', cleaned)
    if cleaned:
        try:
            parsed = json.loads(cleaned)
            if _has_keys(parsed):
                return parsed
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

    # Strategy 4: Ask LLM to repair
    keys_str = f" Ensure the following keys are present: {require_keys}." if require_keys else ""
    fixer_system = (
        "You are a JSON repair bot.\n"
        "Return ONLY valid JSON.\n"
        "No markdown. No explanations.\n"
        f"Fix the user's content into valid JSON, preserving keys and meaning.{keys_str}"
    )

    try:
        fixed = ollama_chat(
            model=model,
            system=fixer_system,
            user=raw,
            temperature=0.0,
            timeout_sec=timeout_sec,
            retries=repair_retries,
            num_predict=repair_num_predict,
        )

        # Try multiple extraction strategies on fixed output
        for candidate in [_extract_json_block(fixed), _strip_fences(fixed), fixed]:
            if candidate:
                try:
                    parsed = json.loads(candidate)
                    if _has_keys(parsed):
                        return parsed
                    if isinstance(parsed, dict):
                        return parsed
                except Exception:
                    continue
    except Exception as repair_err:
        # If repair fails, we'll fall through to the error below
        pass

    # All strategies failed
    raise ValueError(
        f"JSON repair failed. Raw output (first 300 chars): {raw[:300]}... "
        f"Error: Could not parse valid JSON with required keys {require_keys}"
    )
