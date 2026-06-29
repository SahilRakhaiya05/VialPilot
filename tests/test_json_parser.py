from src.vialpilot.utils.json_parse import extract_json


def test_extract_plain_json():
    result = extract_json('{"allow": true, "risk_level": "low"}')
    assert result["allow"] is True
    assert result["risk_level"] == "low"


def test_extract_fenced_json():
    text = '```json\n{"command": "MOVE_TO"}\n```'
    result = extract_json(text)
    assert result["command"] == "MOVE_TO"


def test_extract_embedded_json():
    text = 'Here is the result: {"success": true} thanks.'
    result = extract_json(text)
    assert result["success"] is True


def test_extract_fallback_on_invalid():
    result = extract_json("not json at all", {"fallback": True})
    assert result["fallback"] is True