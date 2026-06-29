from src.vialpilot.agents.safety_veto_agent import safety_veto_agent


def test_safety_veto_blocks_uncertain_command():
    subtask = {
        "id": "T1",
        "target_object": "unclear_vial",
        "destination": "human_confirmation",
        "goal": "Confirm vial identity",
    }
    vision = {
        "objects": [{"id": "unclear_vial", "confidence": 0.4, "label": "blurry vial"}],
        "hazards": [],
    }
    scene = {"hazards": []}

    output = safety_veto_agent.run(subtask, vision, scene)
    assert output.status == "blocked"
    assert output.data["allow"] is False