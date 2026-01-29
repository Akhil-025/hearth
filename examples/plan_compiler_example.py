"""
PLAN COMPILER EXAMPLE - Demonstrates usage and constraints

# LLM reasoning → plan
# No execution authority
# No autonomy
# Fail-closed
"""

from artemis.plan_compiler import (
    PlanCompiler,
    PlanParser,
    StepParseError,
    ValidationError,
    Faculty,
    CapabilityType,
)


def example_1_successful_parse():
    """Example: Successfully parse and compile a plan."""
    print("=" * 70)
    print("EXAMPLE 1: Successful Plan Compilation")
    print("=" * 70)

    llm_output = """
    STEP 1:
    FACULTY: READ_KNOWLEDGE
    ACTION: Query knowledge base for Python decorators
    PARAMETERS: {"search_term": "python decorators", "limit": 5}
    CAPABILITIES: KNOWLEDGE_READ

    STEP 2:
    FACULTY: ANALYZE_CODE
    ACTION: Analyze decorator patterns in retrieved code examples
    PARAMETERS: {"focus": "syntax and semantics"}
    CAPABILITIES: ANALYSIS

    STEP 3:
    FACULTY: PLAN_SCHEDULE
    ACTION: Suggest learning schedule for mastering decorators
    PARAMETERS: {"timeframe": "weekly", "difficulty": "beginner"}
    CAPABILITIES: ANALYSIS
    """

    intent = "Learn about Python decorators with schedule"
    compiler = PlanCompiler()

    try:
        plan = compiler.compile(
            intent=intent,
            llm_output=llm_output,
            security_summary={"state": "SECURE", "execution_allowed": True},
            draft_id="example-1",
        )

        print(f"✓ SUCCESS: Plan compiled with {plan.step_count()} steps")
        print(f"  Intent: {plan.intent}")
        print(f"  Risk level: {plan.estimated_risk_level}")
        print(f"  Faculties: {', '.join(f.value for f in plan.required_faculties)}")
        print(f"  Timestamp: {plan.timestamp}")
        print()

        # Show steps
        for step in plan.derived_steps:
            print(f"  Step {step.sequence}: {step.action}")
            print(f"    Faculty: {step.faculty.value}")
            print(f"    Capabilities: {', '.join(step.required_capabilities)}")
        print()

        return plan

    except (StepParseError, ValidationError) as e:
        print(f"✗ FAILED: {e}")
        return None


def example_2_missing_faculty():
    """Example: Fail-closed on missing FACULTY marker."""
    print("=" * 70)
    print("EXAMPLE 2: Fail-Closed - Missing FACULTY Marker")
    print("=" * 70)

    llm_output = """
    STEP 1:
    ACTION: Do something without specifying faculty
    CAPABILITIES: ANALYSIS
    """

    intent = "Try to do something vague"
    compiler = PlanCompiler()

    try:
        plan = compiler.compile(
            intent=intent,
            llm_output=llm_output,
            security_summary={"state": "SECURE"},
            draft_id="example-2",
        )
        print("✗ ERROR: Should have failed but didn't!")

    except (StepParseError, ValidationError) as e:
        print(f"✓ CORRECTLY REJECTED: {e}")
        print()


def example_3_forbidden_conditional():
    """Example: Fail-closed on conditional keyword in action."""
    print("=" * 70)
    print("EXAMPLE 3: Fail-Closed - Forbidden Conditional Keyword")
    print("=" * 70)

    llm_output = """
    STEP 1:
    FACULTY: READ_MEMORY
    ACTION: If the user has memories, analyze them for patterns
    PARAMETERS: {}
    CAPABILITIES: MEMORY_READ
    """

    intent = "Analyze memories if they exist"
    compiler = PlanCompiler()

    try:
        plan = compiler.compile(
            intent=intent,
            llm_output=llm_output,
            security_summary={"state": "SECURE"},
            draft_id="example-3",
        )
        print("✗ ERROR: Should have failed but didn't!")

    except (StepParseError, ValidationError) as e:
        print(f"✓ CORRECTLY REJECTED: {e}")
        print()


def example_4_ambiguous_step():
    """Example: Fail-closed on ambiguous step."""
    print("=" * 70)
    print("EXAMPLE 4: Fail-Closed - Ambiguous Step (no capabilities)")
    print("=" * 70)

    llm_output = """
    STEP 1:
    FACULTY: READ_KNOWLEDGE
    ACTION: Search for something
    PARAMETERS: {}
    CAPABILITIES:
    """

    intent = "Search for something unclear"
    compiler = PlanCompiler()

    try:
        plan = compiler.compile(
            intent=intent,
            llm_output=llm_output,
            security_summary={"state": "SECURE"},
            draft_id="example-4",
        )
        print("✗ ERROR: Should have failed but didn't!")

    except (StepParseError, ValidationError) as e:
        print(f"✓ CORRECTLY REJECTED: {e}")
        print()


def example_5_immutability():
    """Example: Demonstrate PlanDraft immutability."""
    print("=" * 70)
    print("EXAMPLE 5: PlanDraft Immutability")
    print("=" * 70)

    llm_output = """
    STEP 1:
    FACULTY: READ_KNOWLEDGE
    ACTION: Retrieve Python documentation
    PARAMETERS: {"topic": "exceptions"}
    CAPABILITIES: KNOWLEDGE_READ
    """

    compiler = PlanCompiler()

    try:
        plan = compiler.compile(
            intent="Learn about exceptions",
            llm_output=llm_output,
            security_summary={"state": "SECURE"},
            draft_id="example-5",
        )

        print(f"✓ Plan created: {plan.draft_id}")
        print(f"  Steps (frozen tuple): {type(plan.derived_steps)}")
        print(f"  Faculties (frozen set): {type(plan.required_faculties)}")

        # Attempt to mutate (will fail at the dataclass level)
        try:
            plan.intent = "HACKED!"
            print("✗ ERROR: Should not be able to mutate frozen dataclass!")
        except Exception as e:
            print(f"✓ CORRECTLY BLOCKED mutation: {type(e).__name__}")
        print()

    except (StepParseError, ValidationError) as e:
        print(f"✗ Failed: {e}")


def example_6_security_snapshot():
    """Example: Security summary is captured at compile time."""
    print("=" * 70)
    print("EXAMPLE 6: Security Snapshot Captured at Compile Time")
    print("=" * 70)

    llm_output = """
    STEP 1:
    FACULTY: READ_MEMORY
    ACTION: Query recent memories
    PARAMETERS: {"limit": 10}
    CAPABILITIES: MEMORY_READ
    """

    compiler = PlanCompiler()

    # Compile with DEGRADED security state
    try:
        plan = compiler.compile(
            intent="Review recent memories",
            llm_output=llm_output,
            security_summary={
                "state": "DEGRADED",
                "explanation": "Attack surface reduction active",
                "execution_allowed": False,
            },
            draft_id="example-6",
        )

        print(f"✓ Plan compiled under DEGRADED state")
        print(f"  Security snapshot: {plan.security_summary_snapshot}")
        print(f"  Plan remains executable (security state is snapshot, not gated)")
        print()

    except (StepParseError, ValidationError) as e:
        print(f"✗ Failed: {e}")


def example_7_export_to_dict():
    """Example: Export plan as JSON-serializable dict."""
    print("=" * 70)
    print("EXAMPLE 7: Export Plan to JSON-Serializable Dict")
    print("=" * 70)

    llm_output = """
    STEP 1:
    FACULTY: ANALYZE_HABITS
    ACTION: Analyze user's daily routine
    PARAMETERS: {"time_window": "7_days"}
    CAPABILITIES: ANALYSIS

    STEP 2:
    FACULTY: PLAN_SCHEDULE
    ACTION: Suggest optimizations for routine
    PARAMETERS: {"focus": "productivity"}
    CAPABILITIES: ANALYSIS
    """

    compiler = PlanCompiler()

    try:
        plan = compiler.compile(
            intent="Optimize daily routine",
            llm_output=llm_output,
            security_summary={"state": "SECURE"},
            draft_id="example-7",
        )

        plan_dict = plan.to_dict()

        print(f"✓ Plan exported to dict")
        print(f"  Keys: {', '.join(plan_dict.keys())}")
        print(f"  Step count: {len(plan_dict['steps'])}")
        print(f"  First step action: {plan_dict['steps'][0]['action']}")
        print(f"  Type is JSON-serializable: ", end="")

        import json

        try:
            json.dumps(plan_dict)
            print("Yes ✓")
        except TypeError as e:
            print(f"No ✗ ({e})")
        print()

    except (StepParseError, ValidationError) as e:
        print(f"✗ Failed: {e}")


if __name__ == "__main__":
    print()
    print("PLAN COMPILER EXAMPLES")
    print("Demonstrates: Success, fail-closed behavior, immutability, security awareness")
    print()

    example_1_successful_parse()
    example_2_missing_faculty()
    example_3_forbidden_conditional()
    example_4_ambiguous_step()
    example_5_immutability()
    example_6_security_snapshot()
    example_7_export_to_dict()

    print("=" * 70)
    print("All examples completed")
    print("=" * 70)
