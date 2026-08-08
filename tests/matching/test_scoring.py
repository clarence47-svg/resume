from profile.models import FactCategory

from matching.models import (
    JDRequirement,
    RequirementMatch,
    RequirementPriority,
    SupportLevel,
)
from matching.scoring import calculate_match_scores


def test_required_requirement_has_greater_score_impact() -> None:
    required = JDRequirement(
        id="required",
        text="熟悉 Python",
        category=FactCategory.PROFESSIONAL,
        priority=RequirementPriority.REQUIRED,
        weight=3,
    )
    preferred = JDRequirement(
        id="preferred",
        text="有 Docker 经验优先",
        category=FactCategory.PROFESSIONAL,
        priority=RequirementPriority.PREFERRED,
        weight=1.5,
    )
    required_score, _ = calculate_match_scores(
        [required, preferred],
        [
            RequirementMatch(
                requirement_id="required",
                support_level=SupportLevel.EXACT,
                confidence=1,
            ),
            RequirementMatch(
                requirement_id="preferred",
                support_level=SupportLevel.NONE,
                confidence=0,
            ),
        ],
    )
    preferred_score, _ = calculate_match_scores(
        [required, preferred],
        [
            RequirementMatch(
                requirement_id="required",
                support_level=SupportLevel.NONE,
                confidence=0,
            ),
            RequirementMatch(
                requirement_id="preferred",
                support_level=SupportLevel.EXACT,
                confidence=1,
            ),
        ],
    )
    assert required_score > preferred_score
    assert required_score == 66.7
