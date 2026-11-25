from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel
from app.models.scheme_data.models import EligibilityRule, OperatorType, DataType

class EligibilityResult(BaseModel):
    status: str # POTENTIALLY_ELIGIBLE, NOT_ELIGIBLE, INSUFFICIENT_INFORMATION
    matched_rules: List[dict] = []
    failed_rules: List[dict] = []
    missing_information: List[str] = []
    explanation: str

def parse_value(value_str: str, data_type: DataType) -> Any:
    if data_type == DataType.NUMBER:
        return float(value_str)
    elif data_type == DataType.BOOLEAN:
        return value_str.lower() in ("true", "1", "yes")
    elif data_type == DataType.LIST:
        return [v.strip() for v in value_str.split(",")]
    return value_str

def compare_values(actual: Any, expected: Any, operator: OperatorType, data_type: DataType) -> bool:
    if actual is None:
        return False
        
    # Convert actual to the proper type for safe comparison
    try:
        actual = parse_value(str(actual), data_type)
        expected = parse_value(str(expected), data_type)
    except Exception:
        return False

    if operator == OperatorType.EQUALS:
        return actual == expected
    elif operator == OperatorType.NOT_EQUALS:
        return actual != expected
    elif operator == OperatorType.IN:
        if isinstance(expected, list):
            return actual in expected
        return False
    elif operator == OperatorType.NOT_IN:
        if isinstance(expected, list):
            return actual not in expected
        return False
        
    # Numeric comparisons
    if data_type == DataType.NUMBER:
        if operator == OperatorType.GREATER_THAN:
            return actual > expected
        elif operator == OperatorType.GREATER_THAN_EQUALS:
            return actual >= expected
        elif operator == OperatorType.LESS_THAN:
            return actual < expected
        elif operator == OperatorType.LESS_THAN_EQUALS:
            return actual <= expected

    return False

def evaluate_rule(rule: dict, profile: Dict[str, Any]) -> dict:
    """
    Evaluates a single rule deterministically.
    rule is a dict representation of EligibilityRule.
    """
    field = rule["field"]
    expected_value = rule["value"]
    operator = OperatorType(rule["operator"])
    data_type = DataType(rule["data_type"])
    
    if field not in profile or profile[field] is None:
        return {
            "rule_id": rule.get("id"),
            "field": field,
            "result": "MISSING"
        }
    
    actual_value = profile[field]
    is_match = compare_values(actual_value, expected_value, operator, data_type)
    
    return {
        "rule_id": rule.get("id"),
        "field": field,
        "operator": operator.value,
        "expected": expected_value,
        "actual": actual_value,
        "result": "MATCH" if is_match else "FAIL"
    }

def evaluate_logic_node(node: dict, rules_map: dict, profile: dict) -> dict:
    """
    Recursively evaluate an AST of rule logic.
    node: {"operator": "AND", "rules": [...]} or {"rule_id": "uuid"}
    """
    if "rule_id" in node:
        rule_id = node["rule_id"]
        if rule_id not in rules_map:
            return {"result": "FAIL"} # Broken reference
        return evaluate_rule(rules_map[rule_id], profile)
    
    op = node.get("operator", "AND").upper()
    child_nodes = node.get("rules", [])
    
    results = [evaluate_logic_node(child, rules_map, profile) for child in child_nodes]
    
    if not results:
        return {"result": "MATCH"} # Empty group is true
        
    has_missing = any(r["result"] == "MISSING" for r in results)
    
    if op == "AND":
        if any(r["result"] == "FAIL" for r in results):
            return {"result": "FAIL", "children": results}
        if has_missing:
            return {"result": "MISSING", "children": results}
        return {"result": "MATCH", "children": results}
        
    elif op == "OR":
        if any(r["result"] == "MATCH" for r in results):
            return {"result": "MATCH", "children": results}
        if all(r["result"] == "FAIL" for r in results):
            return {"result": "FAIL", "children": results}
        return {"result": "MISSING", "children": results}
        
    return {"result": "FAIL"}

def flatten_results(node_result: dict, matched: list, failed: list, missing: list):
    if "field" in node_result: # It's a leaf node (rule)
        if node_result["result"] == "MATCH":
            matched.append(node_result)
        elif node_result["result"] == "FAIL":
            failed.append(node_result)
        elif node_result["result"] == "MISSING":
            if node_result["field"] not in missing:
                missing.append(node_result["field"])
    if "children" in node_result:
        for child in node_result["children"]:
            flatten_results(child, matched, failed, missing)

def evaluate_eligibility(profile: Dict[str, Any], rules: List[EligibilityRule], rule_logic: Optional[dict] = None) -> EligibilityResult:
    """
    Evaluates a user profile against scheme rules deterministically.
    """
    if not rules:
        return EligibilityResult(
            status="POTENTIALLY_ELIGIBLE",
            explanation="No specific eligibility rules found."
        )

    rules_map = {str(r.id): {
        "id": str(r.id),
        "field": r.field,
        "operator": r.operator,
        "value": r.value,
        "data_type": r.data_type,
        "is_mandatory": r.is_mandatory
    } for r in rules}

    # If no logic is defined, default to ALL rules must match (Global AND)
    if not rule_logic:
        rule_logic = {
            "operator": "AND",
            "rules": [{"rule_id": r_id} for r_id in rules_map.keys()]
        }
        
    root_result = evaluate_logic_node(rule_logic, rules_map, profile)
    
    matched = []
    failed = []
    missing = []
    
    flatten_results(root_result, matched, failed, missing)
    
    if root_result["result"] == "FAIL":
        status = "NOT_ELIGIBLE"
        explanation = "The user does not meet all required eligibility criteria."
    elif root_result["result"] == "MISSING":
        status = "INSUFFICIENT_INFORMATION"
        explanation = f"Missing information to determine eligibility: {', '.join(missing)}."
    else:
        status = "POTENTIALLY_ELIGIBLE"
        explanation = "Based on provided information, the user appears eligible."
        
    return EligibilityResult(
        status=status,
        matched_rules=matched,
        failed_rules=failed,
        missing_information=missing,
        explanation=explanation
    )
