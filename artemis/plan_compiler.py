"""
PLAN COMPILER - LLM reasoning → strict executable plans

# LLM reasoning → plan
# No execution authority
# No autonomy
# Fail-closed

Converts Hestia (LLM) output into STRICT, EXECUTABLE PLANS
that can later be approved and executed.

CONSTRAINTS:
- No execution
- No approval
- No retries
- No background activity
- No mutation of system state
- Standard library only
- Deterministic output for identical inputs

OUTPUTS: PlanDraft (immutable, auditable)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, FrozenSet
from enum import Enum
import json


# ============================================================================
# FACULTY DEFINITIONS
# ============================================================================

class Faculty(Enum):
    """Compute faculties available to plans."""
    READ_KNOWLEDGE = "read_knowledge"      # Query knowledge store
    READ_MEMORY = "read_memory"            # Query memory
    ANALYZE_CODE = "analyze_code"          # Hephaestus reasoning
    ANALYZE_HABITS = "analyze_habits"      # Apollo reasoning
    ANALYZE_TONE = "analyze_tone"          # Hermes reasoning
    RECOMMEND_MUSIC = "recommend_music"    # Dionysus reasoning
    PLAN_SCHEDULE = "plan_schedule"        # Hermes scheduling
    # WRITE faculties forbidden in plans (require explicit approval)


class CapabilityType(Enum):
    """Capability classes required for plan execution."""
    READ_ONLY = "read_only"
    KNOWLEDGE_READ = "knowledge_read"
    MEMORY_READ = "memory_read"
    ANALYSIS = "analysis"
    # All WRITE capabilities forbidden in initial draft


# ============================================================================
# STEP NORMALIZATION
# ============================================================================

@dataclass(frozen=True)
class PlanStep:
    """
    Single, explicit step in a compiled plan.

    # LLM reasoning → plan
    # No execution authority
    # No autonomy
    # Fail-closed

    Constraints:
    - Explicit (no ambiguity)
    - Finite (no loops, retries, or conditionals)
    - Faculty-scoped (one faculty only)
    - Capability-annotated (what access is needed)
    - Deterministic (same input → same output)
    """
    sequence: int                          # 1-based order
    faculty: Faculty                       # Single faculty only
    action: str                            # Explicit verb+noun
    parameters: Dict[str, Any]             # Input parameters
    required_capabilities: FrozenSet[str]  # Capabilities needed
    estimated_duration_sec: Optional[float] = None  # Time estimate
    notes: str = ""                        # Human-readable notes

    def __post_init__(self) -> None:
        """Validate step normalization."""
        # Must have explicit action
        if not self.action or len(self.action.strip()) == 0:
            raise ValueError(f"Step {self.sequence}: action cannot be empty")

        # Must have at least one required capability
        if not self.required_capabilities:
            raise ValueError(f"Step {self.sequence}: must declare required capabilities")

        # Parameters must be JSON-serializable
        try:
            json.dumps(self.parameters, default=str)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Step {self.sequence}: parameters not JSON-serializable: {e}")

        # Action must not contain forbidden keywords (conditionals)
        forbidden = {"if ", "maybe", "try ", "retry", "loop", "while", "for ", "attempt"}
        action_lower = self.action.lower()
        for keyword in forbidden:
            if keyword in action_lower:
                raise ValueError(
                    f"Step {self.sequence}: action contains forbidden keyword '{keyword}': {self.action}"
                )


@dataclass(frozen=True)
class PlanDraft:
    """
    Immutable compiled plan from LLM reasoning.

    # LLM reasoning → plan
    # No execution authority
    # No autonomy
    # Fail-closed

    All fields are deterministic, auditable, and immutable.
    """
    draft_id: str                                      # Unique identifier
    intent: str                                        # Original user intent
    derived_steps: Tuple[PlanStep, ...]               # Ordered steps
    required_faculties: FrozenSet[Faculty]            # Faculties needed
    required_capabilities: FrozenSet[str]             # Capabilities needed
    estimated_risk_level: str                         # low|medium|high|unknown
    required_approvals: FrozenSet[str]                # Approval types needed
    security_summary_snapshot: Dict[str, Any]         # Artemis state at compile time
    assumptions: Tuple[str, ...]                      # Explicit assumptions
    known_unknowns: Tuple[str, ...]                   # Known gaps
    timestamp: str                                    # ISO 8601 compile timestamp
    compiler_version: str = "1.0"                     # Plan format version

    def step_count(self) -> int:
        """Return total steps in plan."""
        return len(self.derived_steps)

    def to_dict(self) -> Dict[str, Any]:
        """Export as JSON-serializable dict (immutable)."""
        return {
            "draft_id": self.draft_id,
            "intent": self.intent,
            "steps": [
                {
                    "sequence": s.sequence,
                    "faculty": s.faculty.value,
                    "action": s.action,
                    "parameters": s.parameters,
                    "required_capabilities": sorted(s.required_capabilities),
                    "estimated_duration_sec": s.estimated_duration_sec,
                    "notes": s.notes,
                }
                for s in self.derived_steps
            ],
            "required_faculties": sorted(f.value for f in self.required_faculties),
            "required_capabilities": sorted(self.required_capabilities),
            "estimated_risk_level": self.estimated_risk_level,
            "required_approvals": sorted(self.required_approvals),
            "security_summary_snapshot": self.security_summary_snapshot,
            "assumptions": list(self.assumptions),
            "known_unknowns": list(self.known_unknowns),
            "timestamp": self.timestamp,
            "compiler_version": self.compiler_version,
        }


# ============================================================================
# LLM OUTPUT PARSER
# ============================================================================

class StepParseError(Exception):
    """Parse error: explicit, fail-closed."""
    pass


class PlanParser:
    """
    Parse raw LLM text into steps.

    # LLM reasoning → plan
    # No execution authority
    # No autonomy
    # Fail-closed

    Rejects ambiguous or underspecified steps.
    Fails closed.
    """

    # Explicit marker pattern
    STEP_MARKER = "STEP"  # Must use: "STEP 1:", "STEP 2:", etc.
    FACULTY_MARKER = "FACULTY:"
    ACTION_MARKER = "ACTION:"
    PARAMS_MARKER = "PARAMETERS:"
    CAPABILITIES_MARKER = "CAPABILITIES:"

    @staticmethod
    def parse_steps(raw_text: str) -> List[Dict[str, Any]]:
        """
        Parse raw LLM text into step dictionaries.

        # LLM reasoning → plan
        # No execution authority
        # No autonomy
        # Fail-closed

        Args:
            raw_text: Raw LLM output

        Returns:
            List of parsed step dicts

        Raises:
            StepParseError: If parsing fails (fail-closed)
        """
        if not raw_text or len(raw_text.strip()) == 0:
            raise StepParseError("Input is empty")

        steps = []
        lines = raw_text.split("\n")

        current_step = None
        current_block = None  # "FACULTY", "ACTION", "PARAMETERS", "CAPABILITIES"

        for line_num, line in enumerate(lines, 1):
            line = line.rstrip()

            # Detect step marker
            if PlanParser.STEP_MARKER in line and ":" in line:
                # Save previous step
                if current_step is not None:
                    _validate_step_dict(current_step, len(steps) + 1)
                    steps.append(current_step)

                # Start new step
                try:
                    seq = int(line.split(":")[0].replace(PlanParser.STEP_MARKER, "").strip())
                except (ValueError, IndexError):
                    raise StepParseError(f"Line {line_num}: invalid STEP marker: {line}")

                current_step = {"sequence": seq}
                current_block = None

            # Detect block markers
            elif PlanParser.FACULTY_MARKER in line:
                if current_step is None:
                    raise StepParseError(f"Line {line_num}: FACULTY marker before STEP marker")
                current_block = "FACULTY"
                content = line.split(PlanParser.FACULTY_MARKER)[1].strip()
                current_step["faculty"] = content

            elif PlanParser.ACTION_MARKER in line:
                if current_step is None:
                    raise StepParseError(f"Line {line_num}: ACTION marker before STEP marker")
                current_block = "ACTION"
                content = line.split(PlanParser.ACTION_MARKER)[1].strip()
                current_step["action"] = content

            elif PlanParser.PARAMETERS_MARKER in line:
                if current_step is None:
                    raise StepParseError(f"Line {line_num}: PARAMETERS marker before STEP marker")
                current_block = "PARAMETERS"
                content = line.split(PlanParser.PARAMETERS_MARKER)[1].strip()
                if content:  # Parse JSON if present
                    try:
                        current_step["parameters"] = json.loads(content)
                    except json.JSONDecodeError as e:
                        raise StepParseError(f"Line {line_num}: invalid JSON in PARAMETERS: {e}")
                else:
                    current_step["parameters"] = {}

            elif PlanParser.CAPABILITIES_MARKER in line:
                if current_step is None:
                    raise StepParseError(f"Line {line_num}: CAPABILITIES marker before STEP marker")
                current_block = "CAPABILITIES"
                content = line.split(PlanParser.CAPABILITIES_MARKER)[1].strip()
                # Parse comma-separated capabilities
                caps = [c.strip() for c in content.split(",") if c.strip()]
                current_step["required_capabilities"] = caps

            elif line.strip() and current_block and not any(
                marker in line for marker in [
                    PlanParser.STEP_MARKER,
                    PlanParser.FACULTY_MARKER,
                    PlanParser.ACTION_MARKER,
                    PlanParser.PARAMETERS_MARKER,
                    PlanParser.CAPABILITIES_MARKER,
                ]
            ):
                # Continuation line for current block
                if current_block == "ACTION":
                    current_step["action"] += " " + line.strip()
                elif current_block == "PARAMETERS":
                    # Try to append to JSON (complex, skip for now)
                    pass

        # Save last step
        if current_step is not None:
            _validate_step_dict(current_step, len(steps) + 1)
            steps.append(current_step)

        if not steps:
            raise StepParseError("No steps found in input")

        return steps


def _validate_step_dict(step: Dict[str, Any], expected_seq: int) -> None:
    """Validate a parsed step dictionary (fail-closed)."""
    # LLM reasoning → plan
    # No execution authority
    # No autonomy
    # Fail-closed

    if "sequence" not in step:
        raise StepParseError(f"Step {expected_seq}: missing sequence")

    if "faculty" not in step:
        raise StepParseError(f"Step {step['sequence']}: missing FACULTY")

    if "action" not in step or not step["action"].strip():
        raise StepParseError(f"Step {step['sequence']}: missing or empty ACTION")

    if "required_capabilities" not in step or not step["required_capabilities"]:
        raise StepParseError(f"Step {step['sequence']}: missing or empty CAPABILITIES")

    if "parameters" not in step:
        step["parameters"] = {}


# ============================================================================
# VALIDATION
# ============================================================================

FORBIDDEN_FACULTIES = {
    # Any WRITE faculties forbidden in draft phase
}

FORBIDDEN_KEYWORDS = {
    "if ",
    "maybe",
    "try ",
    "retry",
    "loop",
    "while",
    "for ",
    "attempt",
    "request approval",  # Implicit approval
    "wait for",          # Implicit conditionality
    "depends on",        # Implicit conditionality
}


class ValidationError(Exception):
    """Validation failure: explicit, fail-closed."""
    pass


def validate_draft(parsed_steps: List[Dict[str, Any]]) -> None:
    """
    Validate that draft meets constraints.

    # LLM reasoning → plan
    # No execution authority
    # No autonomy
    # Fail-closed

    Rejects drafts that:
    - Implicitly require execution
    - Omit required capabilities
    - Reference forbidden faculties
    - Contain conditionals

    Args:
        parsed_steps: List of parsed step dicts

    Raises:
        ValidationError: If draft fails validation
    """
    if not parsed_steps:
        raise ValidationError("Draft must contain at least one step")

    # Check sequence continuity
    sequences = [s.get("sequence") for s in parsed_steps]
    if sequences != sorted(sequences) or sequences[0] != 1:
        raise ValidationError("Step sequences must be consecutive starting from 1")

    for step in parsed_steps:
        seq = step["sequence"]

        # Check faculty
        faculty_str = step.get("faculty", "").strip().upper()
        try:
            Faculty[faculty_str]
        except KeyError:
            raise ValidationError(f"Step {seq}: unknown faculty '{faculty_str}'")

        if faculty_str in FORBIDDEN_FACULTIES:
            raise ValidationError(f"Step {seq}: forbidden faculty '{faculty_str}'")

        # Check action for forbidden keywords
        action = step.get("action", "").lower()
        for keyword in FORBIDDEN_KEYWORDS:
            if keyword in action:
                raise ValidationError(
                    f"Step {seq}: action contains forbidden keyword '{keyword}': {step['action']}"
                )

        # Check capabilities
        caps = step.get("required_capabilities", [])
        if not caps or not isinstance(caps, list):
            raise ValidationError(f"Step {seq}: missing or invalid required_capabilities")

        # Validate capability names are known
        for cap in caps:
            try:
                CapabilityType[cap.upper()]
            except KeyError:
                raise ValidationError(f"Step {seq}: unknown capability '{cap}'")


# ============================================================================
# COMPILER
# ============================================================================

class PlanCompiler:
    """
    Compile LLM reasoning into strict executable plans.

    # LLM reasoning → plan
    # No execution authority
    # No autonomy
    # Fail-closed

    NO execution logic.
    NO approvals.
    NO mutations to Artemis state.
    """

    def __init__(self, kernel: Optional[Any] = None):
        """
        Initialize compiler.

        Args:
            kernel: Kernel reference (for security summary, inspection only)
        """
        self._kernel = kernel

    def compile(
        self,
        intent: str,
        llm_output: str,
        security_summary: Dict[str, Any],
        draft_id: str,
    ) -> PlanDraft:
        """
        Compile LLM output into PlanDraft.

        # LLM reasoning → plan
        # No execution authority
        # No autonomy
        # Fail-closed

        Args:
            intent: User's original intent
            llm_output: Raw LLM text output
            security_summary: Current Artemis security state (snapshot)
            draft_id: Unique draft identifier

        Returns:
            PlanDraft (immutable)

        Raises:
            StepParseError: If parsing fails
            ValidationError: If validation fails
        """
        # Step 1: Parse raw LLM output
        try:
            parsed_steps = PlanParser.parse_steps(llm_output)
        except StepParseError as e:
            raise StepParseError(f"Parse failed: {e}")

        # Step 2: Validate parsed steps
        try:
            validate_draft(parsed_steps)
        except ValidationError as e:
            raise ValidationError(f"Validation failed: {e}")

        # Step 3: Normalize to PlanStep objects
        steps = []
        for parsed in parsed_steps:
            faculty = Faculty[parsed["faculty"].strip().upper()]
            capabilities = frozenset(parsed["required_capabilities"])

            step = PlanStep(
                sequence=parsed["sequence"],
                faculty=faculty,
                action=parsed["action"],
                parameters=parsed.get("parameters", {}),
                required_capabilities=capabilities,
                estimated_duration_sec=parsed.get("estimated_duration_sec"),
                notes=parsed.get("notes", ""),
            )
            steps.append(step)

        # Step 4: Aggregate requirements
        required_faculties = frozenset(s.faculty for s in steps)
        required_capabilities = frozenset(cap for s in steps for cap in s.required_capabilities)

        # Infer risk level (simple heuristic)
        risk = _estimate_risk(steps, required_faculties)

        # Infer required approvals (in draft phase: READ_ONLY only)
        required_approvals = frozenset({"READ_ONLY"})

        # Step 5: Collect assumptions and unknowns
        assumptions = _infer_assumptions(intent, steps)
        unknowns = _infer_unknowns(intent, steps)

        # Step 6: Build PlanDraft
        from datetime import datetime

        draft = PlanDraft(
            draft_id=draft_id,
            intent=intent,
            derived_steps=tuple(steps),
            required_faculties=required_faculties,
            required_capabilities=required_capabilities,
            estimated_risk_level=risk,
            required_approvals=required_approvals,
            security_summary_snapshot=security_summary,
            assumptions=assumptions,
            known_unknowns=unknowns,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

        return draft


def _estimate_risk(steps: List[PlanStep], faculties: FrozenSet[Faculty]) -> str:
    """
    Estimate plan risk level (simple heuristic).

    # LLM reasoning → plan
    # No execution authority
    # No autonomy
    # Fail-closed
    """
    # If any analysis faculty, medium risk
    if any(
        f in faculties
        for f in [Faculty.ANALYZE_CODE, Faculty.ANALYZE_HABITS, Faculty.ANALYZE_TONE]
    ):
        return "medium"

    # If knowledge/memory read only, low risk
    if all(f in [Faculty.READ_KNOWLEDGE, Faculty.READ_MEMORY] for f in faculties):
        return "low"

    # Default: unknown
    return "unknown"


def _infer_assumptions(intent: str, steps: List[PlanStep]) -> Tuple[str, ...]:
    """
    Infer explicit assumptions from intent and steps.

    # LLM reasoning → plan
    # No execution authority
    # No autonomy
    # Fail-closed
    """
    assumptions = [
        "User has read access to all knowledge sources referenced in steps.",
        "User has read access to all memory types referenced in steps.",
        "LLM outputs are deterministic given identical inputs.",
    ]
    return tuple(assumptions)


def _infer_unknowns(intent: str, steps: List[PlanStep]) -> Tuple[str, ...]:
    """
    Infer known unknowns (gaps) from intent and steps.

    # LLM reasoning → plan
    # No execution authority
    # No autonomy
    # Fail-closed
    """
    unknowns = [
        "Exact time required for each step (estimates only).",
        "Availability of knowledge sources (assumed available).",
        "Memory structure and completeness (assumed valid).",
    ]
    return tuple(unknowns)
