from backend.evaluation.benchmark_answerability import summarize


def test_summary_distinguishes_model_permission_from_final_routing():
    rows = [
        {"expected_can_auto_reply": False, "assessment": {"can_auto_reply": True}, "decision": "ESCALATE"},
        {"expected_can_auto_reply": False, "assessment": {"can_auto_reply": True}, "decision": "AUTO_REPLY"},
        {"expected_can_auto_reply": True, "assessment": {"can_auto_reply": False}, "decision": "ESCALATE"},
        {"expected_can_auto_reply": True, "assessment": {"can_auto_reply": True}, "decision": "AUTO_REPLY"},
    ]
    assert summarize(rows) == {
        "evaluated": 4, "answerability_correct": 1,
        "false_answerability_permissions": 2, "unsafe_auto_reply_decisions": 1,
        "answerable_tickets_escalated": 1,
    }
