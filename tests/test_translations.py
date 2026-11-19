"""Keep translations/en.json in step with strings.json.

Home Assistant only reads translations/en.json for a custom integration;
strings.json is the source file and is ignored at runtime. They drifted once:
fifteen entity names were added to strings.json only, so those entities had no
name, fell back to the channel device name, and got "_2", "_3" entity IDs.
"""

import json
import re
from pathlib import Path

COMPONENT = Path(__file__).parents[1] / "custom_components" / "shure_wireless"


def _load(name: str) -> dict:
    return json.loads((COMPONENT / name).read_text(encoding="utf-8"))


def test_en_json_matches_strings_json() -> None:
    """en.json must be an exact copy of strings.json."""
    assert _load("translations/en.json") == _load("strings.json")


def test_every_entity_translation_key_has_a_name() -> None:
    """Each translation_key used in code has an entity name in en.json."""
    entity = _load("translations/en.json").get("entity", {})
    named = {key for keys in entity.values() for key in keys}
    used = set()
    for path in COMPONENT.glob("*.py"):
        used |= set(re.findall(r"translation_key\s*=\s*\"([a-z0-9_]+)\"", path.read_text()))
    missing = sorted(used - named)
    assert not missing, f"translation keys with no entity name in en.json: {missing}"
