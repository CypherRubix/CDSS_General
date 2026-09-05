from __future__ import annotations

from collections import defaultdict

from .models import Condition, ConditionTest


def build_test_recommendations(condition: Condition) -> list[dict]:
    recommendations: list[dict] = []
    seen: set[int] = set()
    for relation in sorted(condition.tests, key=lambda item: (item.priority, item.test.name.casefold())):
        test = relation.test
        if test.test_id in seen:
            continue
        seen.add(test.test_id)
        recommendations.append(
            {
                "test_id": test.test_id,
                "name": test.name,
                "description": test.description,
                "purpose": relation.purpose or test.purpose,
                "priority": relation.priority,
                "associated_conditions": [condition.name],
            }
        )
    return recommendations


def build_aggregate_test_recommendations(conditions: list[Condition]) -> dict[int, dict]:
    aggregates: dict[int, dict] = {}
    for condition in conditions:
        for recommendation in build_test_recommendations(condition):
            test_id = recommendation["test_id"]
            entry = aggregates.setdefault(
                test_id,
                {
                    "test_id": test_id,
                    "name": recommendation["name"],
                    "description": recommendation["description"],
                    "purpose": recommendation["purpose"],
                    "priority": recommendation["priority"],
                    "associated_conditions": set(),
                },
            )
            entry["associated_conditions"].add(condition.name)
            if recommendation["priority"] < entry["priority"]:
                entry["priority"] = recommendation["priority"]
                entry["purpose"] = recommendation["purpose"]
    final: dict[int, dict] = {}
    for key, value in aggregates.items():
        final[key] = {
            "test_id": value["test_id"],
            "name": value["name"],
            "description": value["description"],
            "purpose": value["purpose"],
            "priority": value["priority"],
            "associated_conditions": sorted(value["associated_conditions"]),
        }
    return final
