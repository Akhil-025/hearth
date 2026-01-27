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
from hestia.agent import HestiaAgent


class HearthApplication:
    """
    Minimal CLI application - accepts one input, produces one output, exits.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.kernel: Optional[HearthKernel] = None
        self.agent: Optional[HestiaAgent] = None
    
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
        config = self.load_configuration()
        self.kernel = HearthKernel(config)
        self.agent = HestiaAgent()
        
        # DISABLED IN v0.1 — no service registration, memory, domains
        # await self.kernel.register_service(self.agent)
    
    async def process_input(self, user_input: str) -> str:
        """Process one input through Hestia."""
        if not self.agent:
            return "ERROR: Agent not initialized"
        
        response = await self.agent.process(user_input)
        return response.text
    
    async def run_once(self) -> int:
        """Accept one CLI input, produce one response, exit."""
        try:
            await self.initialize()
            
            print("HEARTH v0.1 - Minimal Execution Spine")
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


def main() -> int:
    """Main entry point - minimal CLI."""
    # DISABLED IN v0.1 — domain listing, testing, configuration
    app = HearthApplication()
    return asyncio.run(app.run_once())


if __name__ == "__main__":
    sys.exit(main())