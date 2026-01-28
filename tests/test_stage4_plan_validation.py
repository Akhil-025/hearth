"""
Stage-4 Plan Validation Tests

OBJECTIVE: Prove Stage-4 accepts ONLY explicit, user-declared JSON plans with strict validation.

CRITICAL CONSTRAINTS:
- Stage-4 is a NEW layer ABOVE Stage-3
- Stage-3 is LOCKED and cannot be modified
- No autonomy, planning, loops, conditionals, background execution
- No smart defaults, inference, or implicit behavior
- Fail-closed on any validation error

STAGE-4 SCOPE:
- Accept explicit JSON plans only
- Validate strictly before execution
- Reject missing fields, extra fields, invalid types
- Reject circular/forward references
- Pass parameters to Stage-3 verbatim
- Fail closed on any error

WHAT STAGE-4 IS NOT:
- NOT an agent
- NOT autonomous
- NOT a planner
- NOT a decision-maker
- NOT background executor
- NOT a retry system
- NOT a learning system
"""

import pytest
import json
from typing import Dict, Any, List, Optional
from datetime import datetime


# ============================================================================
# STAGE-4 PLAN SCHEMA
# ============================================================================

class Stage4ExecutionPlan:
    """
    Explicit, user-declared execution plan for Stage-4.
    
    Stage-4 accepts ONLY explicit JSON plans. No inference, no defaults, no smart behavior.
    
    Required Fields:
        - user_id: str (who is executing this plan)
        - token_hash: str (Stage-3 token for authorization)
        - trigger_type: str (how plan was triggered, e.g., "direct_command")
        - steps: List[Step] (fixed, explicit sequence of domain invocations)
        - data_bindings: List[DataBinding] (optional, explicit data flow)
    
    CRITICAL:
    - All fields must be present (no defaults)
    - No extra fields allowed (strict validation)
    - Steps order is fixed at creation (no runtime changes)
    - No loops (fixed step count)
    - No conditionals (all steps execute or plan aborts)
    - Immutable after validation
    """
    
    def __init__(
        self,
        user_id: str,
        token_hash: str,
        trigger_type: str,
        steps: List[Dict[str, Any]],
        data_bindings: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Create execution plan from explicit user declaration.
        
        Args:
            user_id: User executing plan
            token_hash: Stage-3 token hash for authorization
            trigger_type: Trigger type (must match token's allowed triggers)
            steps: Fixed list of domain invocation steps
            data_bindings: Optional explicit data flow declarations
        
        Raises:
            ValueError: If validation fails
        """
        # Store fields
        self.user_id = user_id
        self.token_hash = token_hash
        self.trigger_type = trigger_type
        self.steps = steps
        self.data_bindings = data_bindings or []
        
        # Mark as immutable
        self._validated = False
        self._immutable = True
    
    def __setattr__(self, name, value):
        """Prevent modification after validation."""
        if hasattr(self, '_immutable') and self._immutable and hasattr(self, '_validated'):
            raise AttributeError(f"Cannot modify validated plan: {name}")
        super().__setattr__(name, value)


# ============================================================================
# STAGE-4 STRICT VALIDATOR
# ============================================================================

def validate_strict_json_plan(plan_json: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Strictly validate user-declared JSON plan.
    
    Validation Rules:
    1. Required fields present: user_id, token_hash, trigger_type, steps
    2. No extra fields (unknown keys rejected)
    3. Correct types for all fields
    4. Steps is non-empty list
    5. Each step has required fields: domain, method, parameters
    6. No forward references in data_bindings
    7. No circular references in data_bindings
    8. All values JSON-serializable
    
    Args:
        plan_json: User-declared plan as JSON dict
    
    Returns:
        (valid: bool, error_reason: Optional[str])
        - (True, None) if valid
        - (False, reason) if invalid
    
    CRITICAL: This is STRICT validation. No lenient mode. Fail closed.
    """
    # Rule 1: Required fields present
    required_fields = {"user_id", "token_hash", "trigger_type", "steps"}
    missing_fields = required_fields - set(plan_json.keys())
    if missing_fields:
        return (False, f"Missing required fields: {missing_fields}")
    
    # Rule 2: No extra fields (except data_bindings which is optional)
    allowed_fields = {"user_id", "token_hash", "trigger_type", "steps", "data_bindings"}
    extra_fields = set(plan_json.keys()) - allowed_fields
    if extra_fields:
        return (False, f"Unknown fields not allowed: {extra_fields}")
    
    # Rule 3a: user_id must be string
    if not isinstance(plan_json["user_id"], str):
        return (False, f"user_id must be string, got {type(plan_json['user_id']).__name__}")
    
    # Rule 3b: token_hash must be string
    if not isinstance(plan_json["token_hash"], str):
        return (False, f"token_hash must be string, got {type(plan_json['token_hash']).__name__}")
    
    # Rule 3c: trigger_type must be string
    if not isinstance(plan_json["trigger_type"], str):
        return (False, f"trigger_type must be string, got {type(plan_json['trigger_type']).__name__}")
    
    # Rule 4: steps must be non-empty list
    if not isinstance(plan_json["steps"], list):
        return (False, f"steps must be list, got {type(plan_json['steps']).__name__}")
    
    if len(plan_json["steps"]) == 0:
        return (False, "steps must have at least one step")
    
    # Rule 5: Each step must have required fields
    for idx, step in enumerate(plan_json["steps"]):
        if not isinstance(step, dict):
            return (False, f"Step {idx} must be dict, got {type(step).__name__}")
        
        step_required = {"domain", "method", "parameters"}
        step_missing = step_required - set(step.keys())
        if step_missing:
            return (False, f"Step {idx} missing required fields: {step_missing}")
        
        # No extra fields in step
        step_extra = set(step.keys()) - step_required
        if step_extra:
            return (False, f"Step {idx} has unknown fields: {step_extra}")
        
        # domain and method must be strings
        if not isinstance(step["domain"], str):
            return (False, f"Step {idx} domain must be string")
        if not isinstance(step["method"], str):
            return (False, f"Step {idx} method must be string")
        
        # parameters must be dict
        if not isinstance(step["parameters"], dict):
            return (False, f"Step {idx} parameters must be dict")
    
    # Rule 6-7: Validate data_bindings if present
    if "data_bindings" in plan_json:
        data_bindings = plan_json["data_bindings"]
        if not isinstance(data_bindings, list):
            return (False, f"data_bindings must be list, got {type(data_bindings).__name__}")
        
        for idx, binding in enumerate(data_bindings):
            if not isinstance(binding, dict):
                return (False, f"Binding {idx} must be dict")
            
            binding_required = {"source_step", "source_path", "target_step", "target_path"}
            binding_missing = binding_required - set(binding.keys())
            if binding_missing:
                return (False, f"Binding {idx} missing required fields: {binding_missing}")
            
            # No extra fields in binding (except optional expected_type)
            binding_allowed = {"source_step", "source_path", "target_step", "target_path", "expected_type"}
            binding_extra = set(binding.keys()) - binding_allowed
            if binding_extra:
                return (False, f"Binding {idx} has unknown fields: {binding_extra}")
            
            # source_step and target_step must be ints
            if not isinstance(binding["source_step"], int):
                return (False, f"Binding {idx} source_step must be int")
            if not isinstance(binding["target_step"], int):
                return (False, f"Binding {idx} target_step must be int")
            
            # source_path and target_path must be strings
            if not isinstance(binding["source_path"], str):
                return (False, f"Binding {idx} source_path must be string")
            if not isinstance(binding["target_path"], str):
                return (False, f"Binding {idx} target_path must be string")
            
            # Rule 6: No forward references (target must be > source)
            if binding["target_step"] <= binding["source_step"]:
                return (False, f"Binding {idx}: target_step must be after source_step (no circular deps)")
            
            # Validate step indices are in range
            num_steps = len(plan_json["steps"])
            if binding["source_step"] < 0 or binding["source_step"] >= num_steps:
                return (False, f"Binding {idx} source_step {binding['source_step']} out of range")
            if binding["target_step"] < 0 or binding["target_step"] >= num_steps:
                return (False, f"Binding {idx} target_step {binding['target_step']} out of range")
    
    # Rule 8: All values JSON-serializable
    try:
        json.dumps(plan_json)
    except (TypeError, ValueError) as e:
        return (False, f"Plan contains non-JSON-serializable values: {str(e)}")
    
    return (True, None)


# ============================================================================
# TESTS: REQUIRED FIELDS
# ============================================================================

class TestRequiredFields:
    """Test that all required fields must be present."""
    
    def test_valid_minimal_plan(self):
        """Valid plan with all required fields should pass."""
        plan = {
            "user_id": "test_user",
            "token_hash": "test_token_hash",
            "trigger_type": "direct_command",
            "steps": [
                {
                    "domain": "apollo",
                    "method": "analyze_habits",
                    "parameters": {"test": "data"}
                }
            ]
        }
        
        valid, error = validate_strict_json_plan(plan)
        assert valid
        assert error is None
    
    def test_missing_user_id(self):
        """Plan missing user_id should be rejected."""
        plan = {
            "token_hash": "test_token_hash",
            "trigger_type": "direct_command",
            "steps": [{"domain": "apollo", "method": "test", "parameters": {}}]
        }
        
        valid, error = validate_strict_json_plan(plan)
        assert not valid
        assert "user_id" in error
    
    def test_missing_token_hash(self):
        """Plan missing token_hash should be rejected."""
        plan = {
            "user_id": "test_user",
            "trigger_type": "direct_command",
            "steps": [{"domain": "apollo", "method": "test", "parameters": {}}]
        }
        
        valid, error = validate_strict_json_plan(plan)
        assert not valid
        assert "token_hash" in error
    
    def test_missing_trigger_type(self):
        """Plan missing trigger_type should be rejected."""
        plan = {
            "user_id": "test_user",
            "token_hash": "test_token_hash",
            "steps": [{"domain": "apollo", "method": "test", "parameters": {}}]
        }
        
        valid, error = validate_strict_json_plan(plan)
        assert not valid
        assert "trigger_type" in error
    
    def test_missing_steps(self):
        """Plan missing steps should be rejected."""
        plan = {
            "user_id": "test_user",
            "token_hash": "test_token_hash",
            "trigger_type": "direct_command"
        }
        
        valid, error = validate_strict_json_plan(plan)
        assert not valid
        assert "steps" in error


class TestNoExtraFields:
    """Test that extra/unknown fields are rejected."""
    
    def test_extra_field_rejected(self):
        """Plan with unknown field should be rejected."""
        plan = {
            "user_id": "test_user",
            "token_hash": "test_token_hash",
            "trigger_type": "direct_command",
            "steps": [{"domain": "apollo", "method": "test", "parameters": {}}],
            "extra_field": "not_allowed"
        }
        
        valid, error = validate_strict_json_plan(plan)
        assert not valid
        assert "extra_field" in error or "Unknown" in error
    
    def test_multiple_extra_fields_rejected(self):
        """Plan with multiple unknown fields should be rejected."""
        plan = {
            "user_id": "test_user",
            "token_hash": "test_token_hash",
            "trigger_type": "direct_command",
            "steps": [{"domain": "apollo", "method": "test", "parameters": {}}],
            "field1": "value1",
            "field2": "value2"
        }
        
        valid, error = validate_strict_json_plan(plan)
        assert not valid
        assert "Unknown" in error or "field1" in error or "field2" in error


class TestTypeValidation:
    """Test that field types are validated."""
    
    def test_user_id_must_be_string(self):
        """user_id must be string."""
        plan = {
            "user_id": 123,  # Wrong type
            "token_hash": "test_token_hash",
            "trigger_type": "direct_command",
            "steps": [{"domain": "apollo", "method": "test", "parameters": {}}]
        }
        
        valid, error = validate_strict_json_plan(plan)
        assert not valid
        assert "user_id" in error and "string" in error.lower()
    
    def test_token_hash_must_be_string(self):
        """token_hash must be string."""
        plan = {
            "user_id": "test_user",
            "token_hash": 12345,  # Wrong type
            "trigger_type": "direct_command",
            "steps": [{"domain": "apollo", "method": "test", "parameters": {}}]
        }
        
        valid, error = validate_strict_json_plan(plan)
        assert not valid
        assert "token_hash" in error and "string" in error.lower()
    
    def test_steps_must_be_list(self):
        """steps must be list."""
        plan = {
            "user_id": "test_user",
            "token_hash": "test_token_hash",
            "trigger_type": "direct_command",
            "steps": "not_a_list"  # Wrong type
        }
        
        valid, error = validate_strict_json_plan(plan)
        assert not valid
        assert "steps" in error and "list" in error.lower()


class TestStepsValidation:
    """Test that steps are validated correctly."""
    
    def test_empty_steps_rejected(self):
        """Plan with empty steps should be rejected."""
        plan = {
            "user_id": "test_user",
            "token_hash": "test_token_hash",
            "trigger_type": "direct_command",
            "steps": []  # Empty
        }
        
        valid, error = validate_strict_json_plan(plan)
        assert not valid
        assert "at least one step" in error.lower()
    
    def test_step_missing_domain(self):
        """Step missing domain should be rejected."""
        plan = {
            "user_id": "test_user",
            "token_hash": "test_token_hash",
            "trigger_type": "direct_command",
            "steps": [
                {
                    "method": "test",
                    "parameters": {}
                }
            ]
        }
        
        valid, error = validate_strict_json_plan(plan)
        assert not valid
        assert "domain" in error
    
    def test_step_missing_method(self):
        """Step missing method should be rejected."""
        plan = {
            "user_id": "test_user",
            "token_hash": "test_token_hash",
            "trigger_type": "direct_command",
            "steps": [
                {
                    "domain": "apollo",
                    "parameters": {}
                }
            ]
        }
        
        valid, error = validate_strict_json_plan(plan)
        assert not valid
        assert "method" in error
    
    def test_step_missing_parameters(self):
        """Step missing parameters should be rejected."""
        plan = {
            "user_id": "test_user",
            "token_hash": "test_token_hash",
            "trigger_type": "direct_command",
            "steps": [
                {
                    "domain": "apollo",
                    "method": "test"
                }
            ]
        }
        
        valid, error = validate_strict_json_plan(plan)
        assert not valid
        assert "parameters" in error
    
    def test_step_with_extra_field_rejected(self):
        """Step with extra field should be rejected."""
        plan = {
            "user_id": "test_user",
            "token_hash": "test_token_hash",
            "trigger_type": "direct_command",
            "steps": [
                {
                    "domain": "apollo",
                    "method": "test",
                    "parameters": {},
                    "extra": "not_allowed"
                }
            ]
        }
        
        valid, error = validate_strict_json_plan(plan)
        assert not valid
        assert "extra" in error or "unknown" in error.lower()


class TestDataBindingsValidation:
    """Test that data bindings are validated correctly."""
    
    def test_valid_data_bindings(self):
        """Valid data bindings should pass."""
        plan = {
            "user_id": "test_user",
            "token_hash": "test_token_hash",
            "trigger_type": "direct_command",
            "steps": [
                {"domain": "apollo", "method": "test1", "parameters": {}},
                {"domain": "hermes", "method": "test2", "parameters": {}}
            ],
            "data_bindings": [
                {
                    "source_step": 0,
                    "source_path": "data.result",
                    "target_step": 1,
                    "target_path": "input.value"
                }
            ]
        }
        
        valid, error = validate_strict_json_plan(plan)
        assert valid
        assert error is None
    
    def test_binding_missing_source_step(self):
        """Binding missing source_step should be rejected."""
        plan = {
            "user_id": "test_user",
            "token_hash": "test_token_hash",
            "trigger_type": "direct_command",
            "steps": [
                {"domain": "apollo", "method": "test", "parameters": {}},
                {"domain": "hermes", "method": "test", "parameters": {}}
            ],
            "data_bindings": [
                {
                    "source_path": "data.result",
                    "target_step": 1,
                    "target_path": "input.value"
                }
            ]
        }
        
        valid, error = validate_strict_json_plan(plan)
        assert not valid
        assert "source_step" in error
    
    def test_circular_reference_rejected(self):
        """Binding with target <= source should be rejected."""
        plan = {
            "user_id": "test_user",
            "token_hash": "test_token_hash",
            "trigger_type": "direct_command",
            "steps": [
                {"domain": "apollo", "method": "test", "parameters": {}},
                {"domain": "hermes", "method": "test", "parameters": {}}
            ],
            "data_bindings": [
                {
                    "source_step": 1,
                    "source_path": "data.result",
                    "target_step": 0,  # Backward reference
                    "target_path": "input.value"
                }
            ]
        }
        
        valid, error = validate_strict_json_plan(plan)
        assert not valid
        assert "circular" in error.lower() or "after" in error.lower()
    
    def test_binding_to_same_step_rejected(self):
        """Binding with source == target should be rejected."""
        plan = {
            "user_id": "test_user",
            "token_hash": "test_token_hash",
            "trigger_type": "direct_command",
            "steps": [
                {"domain": "apollo", "method": "test", "parameters": {}}
            ],
            "data_bindings": [
                {
                    "source_step": 0,
                    "source_path": "data.result",
                    "target_step": 0,  # Same step
                    "target_path": "input.value"
                }
            ]
        }
        
        valid, error = validate_strict_json_plan(plan)
        assert not valid
    
    def test_binding_out_of_range_source(self):
        """Binding with source step out of range should be rejected."""
        plan = {
            "user_id": "test_user",
            "token_hash": "test_token_hash",
            "trigger_type": "direct_command",
            "steps": [
                {"domain": "apollo", "method": "test", "parameters": {}},
                {"domain": "hermes", "method": "test", "parameters": {}}
            ],
            "data_bindings": [
                {
                    "source_step": 5,  # Out of range
                    "source_path": "data.result",
                    "target_step": 6,
                    "target_path": "input.value"
                }
            ]
        }
        
        valid, error = validate_strict_json_plan(plan)
        assert not valid
        assert "out of range" in error.lower()


class TestJsonSerializable:
    """Test that non-JSON-serializable values are rejected."""
    
    def test_non_serializable_function_rejected(self):
        """Plan with function should be rejected."""
        plan = {
            "user_id": "test_user",
            "token_hash": "test_token_hash",
            "trigger_type": "direct_command",
            "steps": [
                {
                    "domain": "apollo",
                    "method": "test",
                    "parameters": {"func": lambda x: x}  # Not serializable
                }
            ]
        }
        
        valid, error = validate_strict_json_plan(plan)
        assert not valid
        assert "serializable" in error.lower()


class TestPlanImmutability:
    """Test that validated plans are immutable."""
    
    def test_plan_is_immutable_after_validation(self):
        """Plan cannot be modified after validation."""
        plan_json = {
            "user_id": "test_user",
            "token_hash": "test_token_hash",
            "trigger_type": "direct_command",
            "steps": [
                {"domain": "apollo", "method": "test", "parameters": {}}
            ]
        }
        
        plan = Stage4ExecutionPlan(**plan_json)
        # Mark as validated using object.__setattr__ to bypass check
        object.__setattr__(plan, '_validated', True)
        
        # Now attempt to modify should fail
        with pytest.raises(AttributeError):
            plan.user_id = "different_user"


class TestNoAutonomyProof:
    """Prove Stage-4 has NO autonomy."""
    
    def test_validator_has_no_inference(self):
        """Validator cannot infer missing values."""
        # Missing required field
        plan = {
            "user_id": "test_user",
            "token_hash": "test_token_hash",
            "steps": [{"domain": "apollo", "method": "test", "parameters": {}}]
        }
        
        valid, error = validate_strict_json_plan(plan)
        assert not valid  # Must reject, cannot infer trigger_type
    
    def test_validator_has_no_defaults(self):
        """Validator cannot provide default values."""
        # Empty parameters
        plan = {
            "user_id": "test_user",
            "token_hash": "test_token_hash",
            "trigger_type": "direct_command",
            "steps": [{"domain": "apollo", "method": "test", "parameters": {}}]
        }
        
        valid, error = validate_strict_json_plan(plan)
        assert valid  # Empty params is OK, but validator doesn't add anything
        
        # Verify no smart defaults added
        plan_obj = Stage4ExecutionPlan(**plan)
        assert plan_obj.steps[0]["parameters"] == {}  # Still empty
    
    def test_plan_execution_order_is_fixed(self):
        """Plan execution order is determined at creation, not runtime."""
        plan = {
            "user_id": "test_user",
            "token_hash": "test_token_hash",
            "trigger_type": "direct_command",
            "steps": [
                {"domain": "apollo", "method": "test1", "parameters": {}},
                {"domain": "hermes", "method": "test2", "parameters": {}},
                {"domain": "dionysus", "method": "test3", "parameters": {}}
            ]
        }
        
        plan_obj = Stage4ExecutionPlan(**plan)
        
        # Order is fixed in steps list
        assert len(plan_obj.steps) == 3
        assert plan_obj.steps[0]["domain"] == "apollo"
        assert plan_obj.steps[1]["domain"] == "hermes"
        assert plan_obj.steps[2]["domain"] == "dionysus"
        
        # No mechanism to reorder (plan is immutable)


class TestNoDynamicBehavior:
    """Prove Stage-4 has NO dynamic behavior."""
    
    def test_no_conditionals_in_validation(self):
        """Validation logic has no runtime conditionals on user data."""
        # Same plan structure should always produce same validation result
        plan1 = {
            "user_id": "user1",
            "token_hash": "token1",
            "trigger_type": "direct_command",
            "steps": [{"domain": "apollo", "method": "test", "parameters": {"x": 1}}]
        }
        
        plan2 = {
            "user_id": "user2",
            "token_hash": "token2",
            "trigger_type": "direct_command",
            "steps": [{"domain": "apollo", "method": "test", "parameters": {"x": 2}}]
        }
        
        valid1, error1 = validate_strict_json_plan(plan1)
        valid2, error2 = validate_strict_json_plan(plan2)
        
        # Different user_ids but same structure → same validation result
        assert valid1 == valid2
        assert (error1 is None) == (error2 is None)
    
    def test_deterministic_validation(self):
        """Same input → same validation result (deterministic)."""
        plan = {
            "user_id": "test_user",
            "token_hash": "test_token_hash",
            "trigger_type": "direct_command",
            "steps": [{"domain": "apollo", "method": "test", "parameters": {}}]
        }
        
        # Validate multiple times
        results = [validate_strict_json_plan(plan) for _ in range(10)]
        
        # All results must be identical
        assert all(r == results[0] for r in results)


class TestFailClosed:
    """Prove Stage-4 fails closed on ANY error."""
    
    def test_partial_validation_not_allowed(self):
        """If any field is invalid, entire plan is rejected."""
        plan = {
            "user_id": "test_user",
            "token_hash": "test_token_hash",
            "trigger_type": "direct_command",
            "steps": [
                {"domain": "apollo", "method": "test", "parameters": {}},  # Valid
                {"domain": "hermes", "method": "test"},  # Missing parameters
                {"domain": "dionysus", "method": "test", "parameters": {}}  # Valid
            ]
        }
        
        valid, error = validate_strict_json_plan(plan)
        assert not valid  # Entire plan rejected, not just step 1
    
    def test_first_error_aborts_validation(self):
        """Validation stops at first error (fail-fast)."""
        plan = {
            "user_id": 123,  # Error 1: Wrong type
            "token_hash": "test_token_hash",
            "trigger_type": "direct_command",
            "steps": "not_a_list",  # Error 2: Wrong type
            "extra_field": "value"  # Error 3: Extra field
        }
        
        valid, error = validate_strict_json_plan(plan)
        assert not valid
        # Should report first error encountered
        assert error is not None
