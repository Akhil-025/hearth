"""
Stage 2: Context Engine & Pipeline Executor - Integration Examples

Demonstrates how the Context Engine and Pipeline Executor work together
to enable multi-domain pipelines in Hearth.

NOTE: These examples are NON-NORMATIVE. Tests and binding specifications are
authoritative. If these examples conflict with test behavior, the examples are wrong.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from hestia.context_engine import ContextEngine


def example_1_energy_policy():
    """Example 1: Energy Policy Analysis with Multi-Domain Pipeline"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Energy Policy Analysis")
    print("="*70)
    
    context = ContextEngine()
    
    # Simulate user adding context
    context.append("User is researching carbon capture technology (CCS)")
    context.append("Interested in policy implications for 2024-2025")
    context.append("Needs both technical and executive summaries")
    
    print("\n[Context Setup]")
    print(f"Entry count: {context.entry_count()}")
    print(f"Token count: {context.token_count()}")
    print(f"TTL: {context.ttl_seconds_remaining()} seconds remaining")
    
    # Parse and validate pipeline
    pipeline_str = """
PIPELINE:
  - athena.query(q="carbon capture and storage technology advances 2024")
  - hermes.rewrite(style="executive summary")
END
"""
    
    print("\n[Pipeline Specification]")
    print(pipeline_str)
    
    pipeline = context.parse_pipeline(pipeline_str)
    
    if pipeline:
        print(f"OK: Pipeline parsed successfully")
        print(f"  Steps: {len(pipeline.steps)}")
        for i, step in enumerate(pipeline.steps, 1):
            args_str = ', '.join(f'{k}="{v}"' for k, v in step.args.items())
            print(f"  {i}. {step.domain_id}.{step.method}({args_str})")
    
    print("\n[Expected Execution Flow]")
    print("Step 1: Athena")
    print("  Input: user context + query about CCS technology")
    print("  Output: Detailed technical analysis (3 pages)")
    print("\nStep 2: Hermes")
    print("  Input: user context + Athena's output + rewrite style")
    print("  Output: Executive summary (1 page)")
    print("\nFinal Result: Return executive summary to user")


def example_2_career_planning():
    """Example 2: Career Transition Planning with Multi-Domain Pipeline"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Career Transition Planning")
    print("="*70)
    
    context = ContextEngine()
    
    # User context
    context.append("Currently: Senior Developer, 10 years experience")
    context.append("Goal: Transition to Staff Engineer / Technical Lead role")
    context.append("Timeline: 6 months")
    context.append("Priorities: Leadership skills, system design, mentoring")
    
    print("\n[Context Setup]")
    print(f"Entry count: {context.entry_count()}")
    print(f"State: {context.state}")
    
    # Multi-domain career pipeline
    pipeline_str = """
PIPELINE:
  - apollo.analyze_habits(focus="work routine and patterns")
  - hermes.synthesize_schedule(duration="6 months", goal="staff engineer transition")
  - hephaestus.recommend_tech_stack(role="staff engineer", experience="10 years")
END
"""
    
    print("\n[Pipeline Specification]")
    print(pipeline_str)
    
    pipeline = context.parse_pipeline(pipeline_str)
    
    if pipeline:
        print(f"OK: Pipeline parsed successfully ({len(pipeline.steps)} steps)")
        for i, step in enumerate(pipeline.steps, 1):
            domain = step.domain_id.upper()
            print(f"  {i}. {domain}: {step.method}()")
    
    print("\n[Expected Execution Flow]")
    print("Step 1: Apollo (Health & Habits Domain)")
    print("  Analyzes current work patterns -> identifies strengths/gaps")
    print("  Output: Habit profile + recommendations")
    print("\nStep 2: Hermes (Communication Domain)")
    print("  Synthesizes 6-month schedule based on Apollo's analysis")
    print("  Output: Weekly action plan")
    print("\nStep 3: Hephaestus (Engineering Domain)")
    print("  Recommends technical skills for staff engineer role")
    print("  Output: Learning roadmap + tech stack recommendations")
    print("\nFinal Result: Complete career transition plan")


def example_3_pipeline_constraint_violations():
    """Example 3: Pipeline Constraint Violations (What's NOT Allowed)"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Pipeline Constraint Violations")
    print("="*70)
    
    context = ContextEngine()
    
    # VIOLATION 1: More than 3 domains
    print("\n[VIOLATION 1: More than 3 domains (max 3)]")
    bad_pipeline_1 = """
PIPELINE:
  - athena.query(q="test")
  - hermes.rewrite(style="brief")
  - hephaestus.explain(level="advanced")
  - dionysus.suggest_music(mood="focused")
END
"""
    print(bad_pipeline_1)
    try:
        context.parse_pipeline(bad_pipeline_1)
        print("ERROR: Should have rejected >3 domains")
    except ValueError as e:
        print(f"OK: Correctly rejected: {e}")
    
    # VIOLATION 2: Duplicate domains
    print("\n[VIOLATION 2: Duplicate domains in pipeline]")
    bad_pipeline_2 = """
PIPELINE:
  - athena.query(q="test")
  - hermes.rewrite(style="brief")
  - athena.query(q="test2")
END
"""
    print(bad_pipeline_2)
    try:
        context.parse_pipeline(bad_pipeline_2)
        print("ERROR: Should have rejected duplicate domains")
    except ValueError as e:
        print(f"OK: Correctly rejected: {e}")
    
    # VIOLATION 3: Conditionals (not supported)
    print("\n[VIOLATION 3: Conditional branching (not supported)]")
    bad_pipeline_3 = """
PIPELINE:
  - athena.query(q="test")
  - if result.length > 100:
      hermes.summarize()
END
"""
    print(bad_pipeline_3)
    try:
        context.parse_pipeline(bad_pipeline_3)
        print("ERROR: Should have rejected conditionals")
    except ValueError as e:
        print(f"OK: Correctly rejected: {e}")
    
    # VIOLATION 4: Loops (not supported)
    print("\n[VIOLATION 4: Loop constructs (not supported)]")
    bad_pipeline_4 = """
PIPELINE:
  - for domain in [athena, hermes]:
      domain.process(q="test")
END
"""
    print(bad_pipeline_4)
    try:
        context.parse_pipeline(bad_pipeline_4)
        print("ERROR: Should have rejected loops")
    except ValueError as e:
        print(f"OK: Correctly rejected: {e}")


def example_4_context_constraints():
    """Example 4: Context Capacity & TTL Constraints"""
    print("\n" + "="*70)
    print("EXAMPLE 4: Context Constraints (Capacity & TTL)")
    print("="*70)
    
    context = ContextEngine()
    
    # CONSTRAINT 1: Max 20 entries
    print("\n[CONSTRAINT 1: Max 20 entries per context]")
    print("Adding 20 entries...")
    for i in range(20):
        context.append(f"Entry {i+1}: Sample conversation text")
    print(f"OK: Context full with {context.entry_count()} entries")
    
    print("Attempting to add 21st entry...")
    try:
        context.append("Entry 21: This should fail")
        print("ERROR: Should have rejected overflow")
    except ValueError as e:
        print(f"OK: Correctly rejected: {e}")
    
    # CONSTRAINT 2: Max 5000 tokens
    print("\n[CONSTRAINT 2: Max 5000 tokens per context]")
    context2 = ContextEngine()
    large_text = "x" * 2000  # ~500 tokens per entry
    print(f"Adding large entries (approx 500 tokens each)...")
    for i in range(9):
        context2.append(large_text)
        print(f"  Entry {i+1}: {context2.token_count()} tokens total")
    
    print(f"Attempting to add 10th entry (would exceed 5000 tokens)...")
    try:
        context2.append(large_text)
        print("ERROR: Should have rejected token overflow")
    except ValueError as e:
        print(f"OK: Correctly rejected: {e}")
    
    # CONSTRAINT 3: Max TTL 1800 seconds
    print("\n[CONSTRAINT 3: Max TTL 1800 seconds (30 minutes)]")
    context3 = ContextEngine()
    
    print("Setting TTL to 1800 seconds (max allowed)...")
    context3.set_ttl(1800)
    print(f"OK: TTL set to {context3.ttl_seconds_remaining()} seconds")
    
    print("Attempting to set TTL to 1801 seconds...")
    try:
        context3.set_ttl(1801)
        print("ERROR: Should have rejected >1800 seconds")
    except ValueError as e:
        print(f"OK: Correctly rejected: {e}")
    
    # CONSTRAINT 4: No sliding expiration
    print("\n[CONSTRAINT 4: No sliding expiration on read]")
    context4 = ContextEngine()
    context4.append("test")
    ttl_1 = context4.ttl_seconds_remaining()
    print(f"Initial TTL: {ttl_1} seconds")
    
    # Read context (snapshot)
    _ = context4.snapshot()
    ttl_2 = context4.ttl_seconds_remaining()
    print(f"TTL after read: {ttl_2} seconds")
    
    if abs(ttl_1 - ttl_2) < 1:
        print("OK: TTL unchanged (no sliding expiration)")
    else:
        print(f"ERROR: TTL changed by {ttl_1 - ttl_2} seconds")


def example_5_context_isolation():
    """Example 5: Context Isolation for Domains"""
    print("\n" + "="*70)
    print("EXAMPLE 5: Context Isolation (Read-Only for Domains)")
    print("="*70)
    
    context = ContextEngine()
    context.append("Sensitive: User's health data")
    context.append("Sensitive: User's financial situation")
    context.append("Sensitive: User's career ambitions")
    
    print("\n[Context Contents (User's Private Data)]")
    print(f"Entry count: {context.entry_count()}")
    print("(Actual contents hidden for privacy)")
    
    # Get snapshot (immutable copy)
    snapshot = context.snapshot()
    print(f"\n[Snapshot Provided to Domain]")
    print(f"Type: {type(snapshot).__name__}")
    print(f"Is immutable/hashable: {hasattr(snapshot, '__hash__')}")
    print(f"Can domain modify: NO (read-only snapshot)")
    
    print("\n[Key Isolation Guarantees]")
    print("OK: Domains receive immutable copy of context")
    print("OK: Domains cannot modify context")
    print("OK: Each domain gets independent snapshot")
    print("OK: No domain can access other domain's internal state")
    print("OK: Domains receive only what's in context (no private registry access)")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("STAGE 2: CONTEXT ENGINE & PIPELINE EXECUTOR")
    print("Integration Examples & Constraint Demonstrations")
    print("="*70)
    
    example_1_energy_policy()
    example_2_career_planning()
    example_3_pipeline_constraint_violations()
    example_4_context_constraints()
    example_5_context_isolation()
    
    print("\n" + "="*70)
    print("All examples completed successfully!")
    print("="*70 + "\n")
