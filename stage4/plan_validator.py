"""
STAGE-4 PLAN VALIDATOR

Strict JSON plan validation (fail-closed).

No lenient parsing, no inference, no defaults.
All-or-nothing validation: partial validation not allowed.
"""

import json
from typing import Dict, Optional, Any


def validate_strict_json_plan(plan_json: Dict) -> tuple[bool, Optional[str]]:
    """
    Strictly validate JSON plan against Stage-4 schema.
    
    Validation Rules (8 total):
    1. Required fields present (user_id, token_hash, trigger_type, steps)
    2. No extra fields (unknown keys rejected)
    3. Correct field types (string, string, string, list)
    4. Steps must be non-empty list
    5. Each step must have domain, method, parameters
    6. No forward references in data_bindings
    7. No circular references in data_bindings
    8. All values must be JSON-serializable
    
    Fail-Closed Semantics:
    - Partial validation not allowed
    - First error aborts (does not continue checking)
    - Same input always produces same output (deterministic)
    
    Args:
        plan_json: Dictionary representing the plan
    
    Returns:
        tuple: (valid: bool, error_reason: Optional[str])
               (True, None) if valid
               (False, error_message) if invalid
    """
    
    # RULE 1: Required fields must be present
    required_fields = {"user_id", "token_hash", "trigger_type", "steps"}
    if not isinstance(plan_json, dict):
        return (False, "Plan must be a dictionary")
    
    missing_fields = required_fields - set(plan_json.keys())
    if missing_fields:
        return (False, f"Missing required fields: {missing_fields}")
    
    # RULE 2: No extra fields allowed (strict schema)
    allowed_fields = {"user_id", "token_hash", "trigger_type", "steps", "data_bindings"}
    extra_fields = set(plan_json.keys()) - allowed_fields
    if extra_fields:
        return (False, f"Unknown fields not allowed: {extra_fields}")
    
    # RULE 3: Correct types for required fields
    if not isinstance(plan_json.get("user_id"), str):
        return (False, "user_id must be string")
    
    if not isinstance(plan_json.get("token_hash"), str):
        return (False, "token_hash must be string")
    
    if not isinstance(plan_json.get("trigger_type"), str):
        return (False, "trigger_type must be string")
    
    if not isinstance(plan_json.get("steps"), list):
        return (False, "steps must be list")
    
    # RULE 4: Steps must be non-empty
    if len(plan_json.get("steps", [])) == 0:
        return (False, "steps list cannot be empty")
    
    # RULE 5: Each step must have required fields (domain, method, parameters)
    for i, step in enumerate(plan_json.get("steps", [])):
        if not isinstance(step, dict):
            return (False, f"Step {i} must be dictionary")
        
        # Check required step fields
        if "domain" not in step:
            return (False, f"Step {i} missing required field: domain")
        
        if "method" not in step:
            return (False, f"Step {i} missing required field: method")
        
        if "parameters" not in step:
            return (False, f"Step {i} missing required field: parameters")
        
        # Check for extra step fields
        allowed_step_fields = {"domain", "method", "parameters"}
        extra_step_fields = set(step.keys()) - allowed_step_fields
        if extra_step_fields:
            return (False, f"Step {i} has unknown fields: {extra_step_fields}")
    
    # RULE 6 & 7: Validate data_bindings if present
    data_bindings = plan_json.get("data_bindings")
    if data_bindings is not None:
        if not isinstance(data_bindings, list):
            return (False, "data_bindings must be list")
        
        step_count = len(plan_json.get("steps", []))
        
        for i, binding in enumerate(data_bindings):
            if not isinstance(binding, dict):
                return (False, f"Binding {i} must be dictionary")
            
            # Check required binding fields
            if "source_step" not in binding:
                return (False, f"Binding {i} missing required field: source_step")
            
            if "source_path" not in binding:
                return (False, f"Binding {i} missing required field: source_path")
            
            if "target_step" not in binding:
                return (False, f"Binding {i} missing required field: target_step")
            
            if "target_path" not in binding:
                return (False, f"Binding {i} missing required field: target_path")
            
            # Get binding indices
            source_step = binding.get("source_step")
            target_step = binding.get("target_step")
            
            # Check types
            if not isinstance(source_step, int):
                return (False, f"Binding {i} source_step must be integer")
            
            if not isinstance(target_step, int):
                return (False, f"Binding {i} target_step must be integer")
            
            if not isinstance(binding.get("source_path"), str):
                return (False, f"Binding {i} source_path must be string")
            
            if not isinstance(binding.get("target_path"), str):
                return (False, f"Binding {i} target_path must be string")
            
            # Check for out-of-range indices
            if source_step < 0 or source_step >= step_count:
                return (False, f"Binding {i} source_step out of range: {source_step}")
            
            if target_step < 0 or target_step >= step_count:
                return (False, f"Binding {i} target_step out of range: {target_step}")
            
            # RULE 6: No forward references (target must not be before source)
            # RULE 7: No circular references (target must be > source)
            if target_step <= source_step:
                return (False, f"Binding {i} has circular or self-reference: source={source_step}, target={target_step}")
    
    # RULE 8: All values must be JSON-serializable
    try:
        json.dumps(plan_json)
    except (TypeError, ValueError) as e:
        return (False, f"Plan contains non-serializable values: {e}")
    
    # All validations passed
    return (True, None)
