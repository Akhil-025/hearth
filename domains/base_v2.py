"""
HEARTH Domain Interface (v0.2)

Minimal, read-only reasoning modules.

Interface:
    domain.handle(query: str) -> str

Constraints:
    - Return strings only (no side effects)
    - Never write memory
    - Never call other domains
    - Never plan or execute actions
    - Deterministic responses

Artemis Policy Enforcement:
    - Domains enforce allow_domains policy at entry
    - Domains enforce allow_network policy for external calls
    - Fail-closed by design (no exceptions, no retries)
"""

from abc import ABC, abstractmethod


class Domain(ABC):
    """Abstract base class for HEARTH domains.
    
    Domains are read-only reasoning modules that:
    - Take a query string
    - Return a string response
    - Perform no side effects
    - Cannot access memory, knowledge, or other domains
    - Cannot plan or execute actions
    
    Artemis Enforcement:
    - Domain entry point enforces Artemis policy
    - Fail-closed by design
    - Do not bypass
    """

    def __init__(self, kernel=None):
        """
        Initialize domain.
        
        Args:
            kernel: Optional Hearth kernel for policy enforcement
        """
        self._kernel = kernel

    @abstractmethod
    def handle(self, query: str) -> str:
        """Process a query and return a reasoning response.
        
        Args:
            query: User query or request string
            
        Returns:
            str: Domain response (reasoning, suggestions, insights)
            
        Constraints:
            - Must return string only
            - Must be deterministic (same input → same output)
            - Must not write memory
            - Must not call other domains
            - Must not have side effects
        """
        pass
    
    def _enforce_domain_policy(self) -> None:
        """
        Enforce domain execution policy.
        
        Artemis enforcement boundary
        Fail-closed by design
        Do not bypass
        
        Raises:
            RuntimeError: If domain execution is not allowed by policy
        """
        # Artemis fault containment
        # Blast radius limited
        # Fail closed
        # No recovery without restart
        if not self._kernel:
            # No kernel - assume policy allows domains (v0.1 compat)
            return
        
        # ────────────────────────────────────────────────────────────────
        # DOMAIN GATE: Block if Artemis state >= COMPROMISED
        # ────────────────────────────────────────────────────────────────
        # Artemis integrity gate
        # Fail closed
        # No execution past this point
        
        if self._kernel._artemis:
            from artemis.state import SecurityState
            
            artemis_state = self._kernel._artemis.get_state()
            
            # Block domain execution if state is COMPROMISED or LOCKDOWN
            if artemis_state in (SecurityState.COMPROMISED, SecurityState.LOCKDOWN):
                raise RuntimeError(
                    f"Domain execution blocked: Artemis state is {artemis_state.name}"
                )
        
        policy = self._kernel.get_security_policy()
        
        # Artemis enforcement boundary
        # Fail-closed by design
        # Do not bypass
        if not policy.allow_domains:
            artemis_state = (
                self._kernel._artemis.get_state().name
                if self._kernel._artemis else "UNKNOWN"
            )
            if self._kernel and self._kernel._artemis:
                reason = f"Policy blocked domain execution (state: {artemis_state})"
                self._kernel._artemis.record_execution_block("domain", reason)
            raise RuntimeError(
                f"Domain execution blocked by Artemis security policy: {artemis_state}"
            )

    def _contain_domain_failure(self, error: Exception) -> None:
        """
        Contain and escalate domain failures.

        Artemis fault containment
        Blast radius limited
        Fail closed
        No recovery without restart
        """
        if self._kernel and self._kernel._artemis:
            self._kernel._artemis.handle_boundary_error(error, "domain")

        raise RuntimeError(f"Domain execution failed (fail-closed): {error}")
