from app.priority_policy import POLICY_VERSION, determine_priority


def test_critical_critical_is_p1():
    result = determine_priority("critical", "critical")
    assert result.priority == "P1"
    assert result.policy_version == POLICY_VERSION


def test_low_low_is_p4():
    result = determine_priority("low", "low")
    assert result.priority == "P4"


def test_high_medium_is_p2():
    result = determine_priority("high", "medium")
    assert result.priority == "P2"


def test_missing_impact_is_undetermined():
    result = determine_priority(None, "high")
    assert result.priority == "undetermined"
    assert "impact" in result.basis


def test_missing_urgency_is_undetermined():
    result = determine_priority("high", None)
    assert result.priority == "undetermined"


def test_both_missing_is_undetermined():
    result = determine_priority(None, None)
    assert result.priority == "undetermined"


def test_invalid_value_is_undetermined_not_guessed():
    result = determine_priority("extremely-bad", "high")
    assert result.priority == "undetermined"


def test_basis_is_always_populated():
    for impact, urgency in [("low", "low"), (None, None), ("critical", None)]:
        result = determine_priority(impact, urgency)
        assert result.basis
