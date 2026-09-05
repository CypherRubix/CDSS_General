from __future__ import annotations

from .models import Condition


def build_treatment_recommendations(condition: Condition) -> list[dict]:
    recommendations: list[dict] = []
    for relation in sorted(condition.treatments, key=lambda item: (item.priority, item.treatment.name.casefold())):
        recommendations.append(
            {
                "treatment_id": relation.treatment.treatment_id,
                "name": relation.treatment.name,
                "description": relation.treatment.description,
                "treatment_type": relation.treatment.treatment_type,
                "priority": relation.priority,
                "notes": relation.notes,
                "associated_condition": condition.name,
            }
        )
    return recommendations
