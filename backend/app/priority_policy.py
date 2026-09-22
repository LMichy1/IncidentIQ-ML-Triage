"""The M2 implementation of the contract defined in docs/priority_policy.md.

Transparent, versioned, rule-based. Not learned from data — see that doc for
why (ticket-priority fields in bug trackers are self-reported and noisy, not
observed operational severity). Missing or invalid impact/urgency always
yields "undetermined", never a guessed priority.
"""

from __future__ import annotations

from dataclasses import dataclass

POLICY_VERSION = "0.1.0"

IMPACT_LEVELS = ("low", "medium", "high", "critical")
URGENCY_LEVELS = ("low", "medium", "high", "critical")
_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}

# The full set of values this policy can ever produce — reused to validate
# a reviewer's corrected_priority in feedback submissions, so a correction
# can't introduce a priority value the policy itself couldn't have.
VALID_PRIORITY_VALUES = frozenset({"P1", "P2", "P3", "P4", "undetermined"})


@dataclass
class PriorityResult:
    priority: str  # "P1".."P4" or "undetermined"
    policy_version: str
    basis: str


def determine_priority(impact: str | None, urgency: str | None) -> PriorityResult:
    if impact not in _RANK or urgency not in _RANK:
        return PriorityResult(
            priority="undetermined",
            policy_version=POLICY_VERSION,
            basis=(
                f"impact={impact!r} and/or urgency={urgency!r} missing or "
                f"outside the known domain {IMPACT_LEVELS} — human "
                "assessment required."
            ),
        )

    score = _RANK[impact] + _RANK[urgency]
    if score >= 7:
        priority = "P1"
    elif score >= 5:
        priority = "P2"
    elif score >= 3:
        priority = "P3"
    else:
        priority = "P4"

    basis = (
        f"impact={impact} (rank {_RANK[impact]}) + urgency={urgency} "
        f"(rank {_RANK[urgency]}) = {score} -> {priority} "
        f"(policy {POLICY_VERSION})"
    )
    return PriorityResult(priority=priority, policy_version=POLICY_VERSION, basis=basis)
