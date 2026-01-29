"""
HEARTH Main - Minimal Execution Spine (v0.1)
"""
import asyncio
import sys
from typing import Optional

# DISABLED IN v0.1 — not part of execution spine
# from mnemosyne.memory_store import MemoryStore
# from domains.hermes.service import HermesService
# from domains.hephaestus.service import HephaestusService
# from domains.apollo.service import ApolloService
# from domains.dionysus.service import DionysusService

from core.kernel import HearthKernel, KernelConfig
from core.bootstrap import bootstrap_hearth
from hestia.agent import HestiaAgent


class HearthApplication:
    """
    CLI application with optional LLM reasoning and memory.
    
    Config:
    - enable_llm: Enable Ollama-based reasoning (default: False)
    - enable_memory: Enable append-only memory with user confirmation (default: False)
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        enable_llm: bool = False,
        enable_memory: bool = False
    ):
        self.kernel: Optional[HearthKernel] = None
        self.agent: Optional[HestiaAgent] = None
        self.enable_llm = enable_llm
        self.enable_memory = enable_memory
    
    def load_configuration(self) -> KernelConfig:
        """Load minimal hardcoded configuration."""
        return KernelConfig(
            data_dir="./data",
            log_level="INFO",
            enable_audit=False,  # DISABLED IN v0.1
            require_permissions=False  # DISABLED IN v0.1
        )
    
    async def initialize(self) -> None:
        """Initialize minimal execution spine."""
        # ARTEMIS FIRST: Bootstrap security authority (passive during boot)
        artemis = bootstrap_hearth()
        
        # ────────────────────────────────────────────────────────────────
        # BOOT GATE: Integrity verification at startup
        # ────────────────────────────────────────────────────────────────
        # Artemis integrity gate
        # Fail closed
        # No execution past this point
        
        try:
            from pathlib import Path
            is_valid, mismatches = artemis.verify_integrity()
            
            if not is_valid:
                # Integrity check failed - Artemis escalated state
                artemis_state = artemis.get_state().name
                print(f"[Artemis] BOOT GATE: Integrity verification failed")
                print(f"[Artemis] State escalated to: {artemis_state}")
                
                for mismatch in mismatches:
                    print(f"  - {mismatch['file']}: {mismatch['status']}")
                
                # Fail closed: Abort boot if state != SECURE or DEGRADED
                if artemis_state not in ["SECURE", "DEGRADED"]:
                    raise RuntimeError(
                        f"Boot aborted: Artemis state {artemis_state} "
                        "disallows execution (integrity gate failed)"
                    )
        except RuntimeError as e:
            # Integrity verification failed catastrophically
            raise RuntimeError(f"Boot integrity gate failed: {e}")
        
        # Log security state (passive observation only)
        from artemis.boundary import (
            POLICY_SECURE, POLICY_DEGRADED,
            POLICY_COMPROMISED, POLICY_LOCKDOWN
        )
        policy_name_map = {
            id(POLICY_SECURE): "SECURE",
            id(POLICY_DEGRADED): "DEGRADED",
            id(POLICY_COMPROMISED): "COMPROMISED",
            id(POLICY_LOCKDOWN): "LOCKDOWN",
        }
        current_policy = artemis.current_policy()
        policy_name = policy_name_map.get(id(current_policy), "UNKNOWN")
        
        print(f"[Artemis] Security state: {artemis.get_state().name}")
        print(f"[Artemis] Active policy: {policy_name}")
        
        config = self.load_configuration()
        self.kernel = HearthKernel(config, artemis=artemis)
        
        # Create agent with optional LLM and memory
        agent_config = {
            "enable_llm": self.enable_llm,
            "enable_memory": self.enable_memory
        }
        self.agent = HestiaAgent(agent_config, kernel=self.kernel)
        
        # Initialize agent (will setup LLM if enabled)
        await self.agent.initialize()
        
        # DISABLED IN v0.1 — no service registration, domains
        # await self.kernel.register_service(self.agent)
    
    async def process_input(self, user_input: str) -> str:
        """Process one input through Hestia, with optional memory confirmation."""
        if not self.agent:
            return "ERROR: Agent not initialized"
        
        # Get response
        response = await self.agent.process(user_input)
        
        # Check if we should offer to remember this
        if self.agent.should_offer_memory(user_input, response.intent):
            if self.agent.prompt_memory_confirmation(user_input):
                if self.agent.save_memory(user_input, response.intent):
                    print("Memory saved.")
                    response.memory_saved = True
                else:
                    print("Failed to save memory.")
            else:
                print("Okay, I won't save it.")
        
        return response.text
    
    async def run_once(self) -> int:
        """Accept one CLI input, produce one response, exit."""
        try:
            await self.initialize()
            
            # Build mode description
            modes = []
            if self.enable_llm:
                modes.append("LLM")
            if self.enable_memory:
                modes.append("Memory")
            mode = " + ".join(modes) if modes else "deterministic"
            
            print(f"HEARTH v0.1 - Minimal Execution Spine ({mode})")
            print("Enter input: ", end="", flush=True)
            user_input = input()
            
            if not user_input.strip():
                print("No input provided")
                return 0
            
            response = await self.process_input(user_input)
            print(f"Response: {response}")
            
            return 0
            
        except KeyboardInterrupt:
            print("\nShutdown requested")
            return 0
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 1
        finally:
            await self.cleanup()
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self.agent:
            await self.agent.cleanup()


def main() -> int:
    """Main entry point - minimal CLI with optional LLM and memory."""
    import argparse
    
    parser = argparse.ArgumentParser(description="HEARTH v0.1 - Minimal Execution Spine")
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Enable LLM reasoning via Ollama (requires Ollama running)"
    )
    parser.add_argument(
        "--memory",
        action="store_true",
        help="Enable append-only memory with user confirmation"
    )
    
    args = parser.parse_args()
    
    app = HearthApplication(enable_llm=args.llm, enable_memory=args.memory)
    return asyncio.run(app.run_once())


if __name__ == "__main__":
    sys.exit(main())