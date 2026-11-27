"""Action engine: turns score triggers (overrides, recurring findings, overdue audits) into owned, dated actions."""

from datetime import date, timedelta


def _matches(rule: dict, trigger: dict) -> bool:
    if rule["trigger"] != trigger["type"]:
        return False
    when = rule.get("when", {})
    if "category" in when and trigger.get("category") != when["category"]:
        return False
    if "min_count" in when and trigger.get("count", 0) < when["min_count"]:
        return False
    return True


def watched_table(rule: dict) -> str:
    """The table whose new upload ends a completed action's effect (so the action can be raised again)."""
    return rule.get("resolves") or "inspections"


def plan_actions(result: dict, rules: dict, as_of: date) -> list[dict]:
    planned: dict[str, dict] = {}
    for trigger in result["triggers"]:
        rule = next((r for r in rules["actions"] if _matches(r, trigger)), None)
        if rule is None:
            continue
        key = f"{result['vessel_id']}:{rule['id']}:{trigger['subject']}"
        if key in planned:
            continue
        planned[key] = {
            "vessel_id": result["vessel_id"],
            "rule_id": rule["id"],
            "action_key": key,
            "text": rule["text"].format(record_ids=", ".join(trigger["record_ids"]), subject=trigger["subject"]),
            "owner": rule["owner"],
            "deadline_days": rule["deadline_days"],
            "deadline_label": rule.get("deadline_label"),
            "due_date": as_of + timedelta(days=rule["deadline_days"]),
            "record_ids": trigger["record_ids"],
            "resolves": {rule["resolves"]: trigger["record_ids"]} if rule.get("resolves") else {},
        }
    return list(planned.values())
