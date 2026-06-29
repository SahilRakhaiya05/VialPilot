from src.vialpilot.llm.cerebras_models import GEMMA4_DEFAULT_MODEL, pick_gemma4_model


def test_pick_gemma4_from_api_list():
    ids = ["gpt-oss-120b", "zai-glm-4.7", "gemma-4-31b"]
    assert pick_gemma4_model(ids) == "gemma-4-31b"


def test_pick_gemma4_auto_falls_back_to_default():
    assert pick_gemma4_model([], configured="auto") == GEMMA4_DEFAULT_MODEL


def test_pick_gemma4_explicit_override():
    assert pick_gemma4_model(["other"], configured="gemma-4-31b") == "gemma-4-31b"