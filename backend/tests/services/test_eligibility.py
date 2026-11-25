from app.services.eligibility.engine import evaluate_eligibility, OperatorType, DataType
from app.models.scheme_data.models import EligibilityRule

import uuid

def create_rule(field, op, val, dtype, group_id=None):
    r = EligibilityRule()
    r.id = str(uuid.uuid4())
    r.field = field
    r.operator = op
    r.value = val
    r.data_type = dtype
    r.group_id = group_id
    r.is_mandatory = True
    return r

def test_eligibility_comparisons():
    rules = [
        create_rule("age", OperatorType.GREATER_THAN_EQUALS, "60", DataType.NUMBER),
        create_rule("income", OperatorType.LESS_THAN, "100000", DataType.NUMBER),
        create_rule("state", OperatorType.EQUALS, "MP", DataType.STRING),
    ]
    
    # Passing profile
    profile = {"age": 65, "income": 50000, "state": "MP"}
    result = evaluate_eligibility(profile, rules)
    assert result.status == "POTENTIALLY_ELIGIBLE"
    assert len(result.failed_rules) == 0
    assert len(result.matched_rules) == 3

def test_boundary_values():
    rules = [
        create_rule("age", OperatorType.GREATER_THAN_EQUALS, "60", DataType.NUMBER)
    ]
    result1 = evaluate_eligibility({"age": 60}, rules)
    assert result1.status == "POTENTIALLY_ELIGIBLE"
    
    result2 = evaluate_eligibility({"age": 59}, rules)
    assert result2.status == "NOT_ELIGIBLE"

def test_type_mismatch():
    rules = [create_rule("age", OperatorType.GREATER_THAN_EQUALS, "60", DataType.NUMBER)]
    # string that can't be parsed
    result = evaluate_eligibility({"age": "sixty"}, rules)
    assert result.status == "NOT_ELIGIBLE"

def test_missing_information():
    rules = [
        create_rule("age", OperatorType.GREATER_THAN_EQUALS, "60", DataType.NUMBER),
        create_rule("income", OperatorType.LESS_THAN, "100000", DataType.NUMBER)
    ]
    
    # Missing income
    profile = {"age": 65}
    result = evaluate_eligibility(profile, rules)
    assert result.status == "INSUFFICIENT_INFORMATION"
    assert "income" in result.missing_information

def test_and_logic():
    rules = [
        create_rule("age", OperatorType.GREATER_THAN_EQUALS, "60", DataType.NUMBER, group_id="g1"),
        create_rule("gender", OperatorType.EQUALS, "F", DataType.STRING, group_id="g1")
    ]
    rule_logic = {
        "operator": "AND",
        "rules": [{"rule_id": rules[0].id}, {"rule_id": rules[1].id}] 
    }
    result = evaluate_eligibility({"age": 65, "gender": "F"}, rules, rule_logic)
    assert result.status == "POTENTIALLY_ELIGIBLE"
    
    result2 = evaluate_eligibility({"age": 65, "gender": "M"}, rules, rule_logic)
    assert result2.status == "NOT_ELIGIBLE"

def test_or_logic():
    rules = [
        create_rule("age", OperatorType.GREATER_THAN_EQUALS, "60", DataType.NUMBER, group_id="g1"),
        create_rule("disability", OperatorType.EQUALS, "true", DataType.BOOLEAN, group_id="g1")
    ]
    rule_logic = {
        "operator": "OR",
        "rules": [{"rule_id": rules[0].id}, {"rule_id": rules[1].id}]
    }
    # Meets one of the OR conditions
    result = evaluate_eligibility({"age": 50, "disability": "true"}, rules, rule_logic)
    assert result.status == "POTENTIALLY_ELIGIBLE"
