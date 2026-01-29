# ARES — Active Defense & Deterrence
# Phase 0: Detection, Deception, Reporting
# No execution authority
# No persistence
# No autonomy
# Reports to Artemis only

"""
ARES is a security subsystem for HEARTH.

Authority Model:
- Artemis = Law (makes final decisions)
- ARES = War (detects, slows, misleads, observes, reports)

ARES has NO authority to:
- Approve or deny plans
- Modify plans
- Talk to users
- Access networks
- Persist data
- Kill the system
- Override Artemis

ARES can only:
- Observe passively
- Report findings to Artemis
- Emit deceptive responses
- Record evidence

Interface:
- report_to_artemis() → AresForensicReport (ONLY method exposed)

State:
- Ephemeral only (in-memory, cleared on restart)
- No disk persistence
- No environment mutation
"""

from .interface import report_to_artemis, AresForensicReport

__all__ = ["report_to_artemis", "AresForensicReport"]
