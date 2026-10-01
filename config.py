"""
Configuration loader and validator for DeltaRadar.
Reads YAML config and merges with environment variables.
"""
import os
import re
from typing import Dict, Any, List

def _simple_yaml_parse(text: str) -> Dict[str, Any]:
    """
    Robust lightweight YAML parser for key-value structures, lists, and dicts.
    """
    lines = text.splitlines()
    
    def parse_block(start_i: int, min_indent: int):
        i = start_i
        # Determine if this block is a list or dict by inspecting the first non-comment line
        block_is_list = False
        first_line_idx = -1
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                i += 1
                continue
            indent = len(line) - len(line.lstrip(" "))
            if indent < min_indent:
                break
            first_line_idx = i
            block_is_list = stripped.startswith("- ")
            break

        if first_line_idx == -1:
            return {}, start_i

        i = first_line_idx
        if block_is_list:
            result_list = []
            while i < len(lines):
                line = lines[i]
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    i += 1
                    continue
                indent = len(line) - len(line.lstrip(" "))
                if indent < min_indent:
                    break
                if not stripped.startswith("- "):
                    # Might be part of previous element or indentation shift
                    break

                val_part = stripped[2:].strip()
                if ":" in val_part and not (val_part.startswith('"') or val_part.startswith("'")):
                    # It's a dict item inside a list! e.g. - symbol: "XAUUSD"
                    item_dict = {}
                    k, v_raw = val_part.split(":", 1)
                    k = k.strip().strip('"').strip("'")
                    v_raw = v_raw.strip()
                    item_dict[k] = _parse_val(v_raw)
                    i += 1
                    # Check for sibling keys under this list item
                    item_indent = indent + 2
                    while i < len(lines):
                        sub_line = lines[i]
                        sub_stripped = sub_line.strip()
                        if not sub_stripped or sub_stripped.startswith("#"):
                            i += 1
                            continue
                        sub_indent = len(sub_line) - len(sub_line.lstrip(" "))
                        if sub_indent < item_indent or sub_stripped.startswith("- "):
                            break
                        if ":" in sub_stripped:
                            sk, sv_raw = sub_stripped.split(":", 1)
                            sk = sk.strip().strip('"').strip("'")
                            item_dict[sk] = _parse_val(sv_raw.strip())
                        i += 1
                    result_list.append(item_dict)
                else:
                    result_list.append(_parse_val(val_part))
                    i += 1
            return result_list, i
        else:
            result_dict = {}
            while i < len(lines):
                line = lines[i]
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    i += 1
                    continue
                indent = len(line) - len(line.lstrip(" "))
                if indent < min_indent:
                    break
                if ":" not in stripped:
                    i += 1
                    continue

                parts = stripped.split(":", 1)
                k = parts[0].strip().strip('"').strip("'")
                v_raw = parts[1].strip()

                if not v_raw or v_raw.startswith("#"):
                    # Nested block
                    nested, next_i = parse_block(i + 1, indent + 1)
                    result_dict[k] = nested
                    i = next_i
                else:
                    result_dict[k] = _parse_val(v_raw)
                    i += 1
            return result_dict, i

    parsed, _ = parse_block(0, 0)
    return parsed

def _parse_val(val_str: str) -> Any:
    # Strip comments
    if " #" in val_str:
        val_str = val_str.split(" #")[0].strip()
    val_str = val_str.strip('"').strip("'")
    if val_str.lower() == "true":
        return True
    if val_str.lower() == "false":
        return False
    if val_str.lower() in ("null", "none"):
        return None
    if val_str.startswith("[") and val_str.endswith("]"):
        inner = val_str[1:-1].strip()
        if not inner:
            return []
        return [_parse_val(x.strip()) for x in inner.split(",")]
    try:
        if "." in val_str:
            return float(val_str)
        return int(val_str)
    except ValueError:
        return val_str

def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Loads configuration from YAML with fallback and environment variable override."""
    if not os.path.exists(config_path):
        # Look in current directory or parent directory
        alt_path = os.path.join(os.path.dirname(__file__), "..", config_path)
        if os.path.exists(alt_path):
            config_path = alt_path

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()

    try:
        import yaml
        config = yaml.safe_load(content)
    except ImportError:
        config = _simple_yaml_parse(content)

    # Allow environment variable overrides
    if "TELEGRAM_BOT_TOKEN" in os.environ:
        config.setdefault("telegram", {})["bot_token"] = os.environ["TELEGRAM_BOT_TOKEN"]
    if "TELEGRAM_CHAT_ID" in os.environ:
        config.setdefault("telegram", {})["chat_id"] = os.environ["TELEGRAM_CHAT_ID"]
    if "GEMINI_API_KEY" in os.environ:
        config.setdefault("ai", {})["gemini_api_key"] = os.environ["GEMINI_API_KEY"]

    return config
