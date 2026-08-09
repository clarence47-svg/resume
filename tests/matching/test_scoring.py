from profile.models import FactCategory, ProfileFact

from matching.models import (
    CapabilityDimension,
    JDAnalysis,
    JDRequirement,
    RequirementMatch,
    RequirementPriority,
    SupportLevel,
)
from matching.scoring import calculate_match_scores, material_relevance_scores


def test_required_requirement_has_greater_score_impact() -> None:
    required = JDRequirement(
        id="required",
        text="熟悉 Python",
        category=FactCategory.CAPABILITY,
        priority=RequirementPriority.REQUIRED,
        weight=3,
    )
    preferred = JDRequirement(
        id="preferred",
        text="有 Docker 经验优先",
        category=FactCategory.CAPABILITY,
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


def test_material_relevance_uses_four_weighted_dimensions() -> None:
    exact_fact = ProfileFact(
        id="exact-fact",
        category=FactCategory.PROJECT,
        statement="主导 Python 服务优化，接口耗时降低 40%",
        confidence=0.95,
    )
    partial_fact = ProfileFact(
        id="partial-fact",
        category=FactCategory.PROJECT,
        statement="参与数据服务开发与团队协作",
        confidence=0.8,
    )
    requirement = JDRequirement(
        id="python",
        text="熟悉 Python 服务开发",
        category=FactCategory.PROJECT,
        priority=RequirementPriority.REQUIRED,
        weight=3,
        keywords=["Python", "服务开发"],
    )
    dimension = CapabilityDimension(
        id="backend",
        name="编程与开发",
        keywords=["Python", "服务开发"],
        requirement_ids=[requirement.id],
    )
    scores = material_relevance_scores(
        JDAnalysis(requirements=[requirement], capability_dimensions=[dimension]),
        [
            RequirementMatch(
                requirement_id=requirement.id,
                support_level=SupportLevel.EXACT,
                source_fact_ids=[exact_fact.id],
                confidence=0.95,
            ),
            RequirementMatch(
                requirement_id=requirement.id,
                support_level=SupportLevel.PARTIAL,
                source_fact_ids=[partial_fact.id],
                confidence=0.8,
            ),
        ],
        [exact_fact, partial_fact],
    )
    assert scores[exact_fact.id].direct_match == 100
    assert scores[exact_fact.id].impact > scores[partial_fact.id].impact
    assert scores[exact_fact.id].overall > scores[partial_fact.id].overall
    assert scores[exact_fact.id].capability_scores[dimension.id] == 100
