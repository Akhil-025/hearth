"""
STAGE-4 CLI ADAPTER

Minimal, deterministic command-line interface for Stage-4 execution.

This is a TRANSPORT ONLY - no inference, no defaults, no enrichment.

Usage:
    python stage4_cli.py <plan_file>

Where <plan_file> is a JSON file containing a Stage-4 execution plan.

Behavior:
1. Load JSON from file (verbatim, no mutation)
2. Validate using validate_strict_json_plan()
3. If invalid: print error, exit(1)
4. If valid: construct Stage4ExecutionPlan
5. Execute via Stage4Orchestrator
6. Print result or error
7. Exit(0 on success, 1 on failure)

Constraints:
- No defaults, no inference, no enrichment
- No retries, no loops, no branching
- Fail-closed on any error
- Standard library only
"""

import argparse
import json
import sys
from typing import Optional, Dict, Any

from stage4 import (
    Stage4ExecutionPlan,
    validate_strict_json_plan,
    Stage4Orchestrator
)


class MockStage3Orchestrator:
    """
    Minimal mock Stage-3 orchestrator for CLI testing.
    
    In production, this would connect to a real Stage-3 service.
    For CLI purposes, we provide a basic mock that demonstrates
    how Stage-4 calls Stage-3.
    """
    
    def execute_multi_domain_plan(
        self,
        user_id: str,
        token_hash: str,
        trigger_type: str,
        steps: list,
        data_bindings: Optional[list] = None
    ) -> Dict[str, Any]:
        """Execute plan through mock Stage-3."""
        # In production, this would validate token, domain, methods, etc.
        # For now, just echo success
        return {
            "status": "completed",
            "user_id": user_id,
            "trigger_type": trigger_type,
            "step_count": len(steps),
            "results": [{"step": i, "output": f"step_{i}_executed"} for i in range(len(steps))]
        }


def load_json_file(filepath: str) -> Optional[Dict]:
    """
    Load JSON from file.
    
    Returns:
        dict if successful
        None if file not found or JSON is invalid
    """
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error: Failed to read file: {e}", file=sys.stderr)
        return None


def main():
    """Main CLI entrypoint."""
    
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Stage-4 execution CLI adapter"
    )
    parser.add_argument(
        "plan_file",
        help="Path to JSON file containing Stage-4 execution plan"
    )
    
    args = parser.parse_args()
    plan_file = args.plan_file
    
    # STEP 1: Load JSON from file (verbatim, no mutation)
    plan_json = load_json_file(plan_file)
    if plan_json is None:
        sys.exit(1)
    
    # STEP 2: Validate plan using strict validator
    valid, error = validate_strict_json_plan(plan_json)
    if not valid:
        print(f"Validation failed: {error}", file=sys.stderr)
        sys.exit(1)
    
    # STEP 3: Construct Stage4ExecutionPlan from validated data
    try:
        plan = Stage4ExecutionPlan(
            user_id=plan_json["user_id"],
            token_hash=plan_json["token_hash"],
            trigger_type=plan_json["trigger_type"],
            steps=plan_json["steps"],
            data_bindings=plan_json.get("data_bindings")
        )
    except Exception as e:
        print(f"Error: Failed to construct plan: {e}", file=sys.stderr)
        sys.exit(1)
    
    # STEP 4: Create Stage-4 orchestrator with Stage-3
    # In production, stage3_orchestrator would be a real Stage-3 service
    # For CLI testing, we use a mock
    try:
        stage3_orchestrator = MockStage3Orchestrator()
        orchestrator = Stage4Orchestrator(stage3_orchestrator)
    except Exception as e:
        print(f"Error: Failed to initialize orchestrator: {e}", file=sys.stderr)
        sys.exit(1)
    
    # STEP 5: Execute plan (fail-closed)
    try:
        result = orchestrator.execute_plan(plan)
    except RuntimeError as e:
        # Execution failed (fail-closed)
        print(f"Execution failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        # Unexpected error (fail-closed)
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    # STEP 6: Print result
    try:
        print(json.dumps(result, indent=2, default=str))
    except Exception as e:
        print(f"Error: Failed to serialize result: {e}", file=sys.stderr)
        sys.exit(1)
    
    # STEP 7: Exit successfully
    sys.exit(0)


if __name__ == "__main__":
    main()
