"""
HEARTH Main - Updated with Domain Intelligence Modules
"""
import asyncio
import logging
import sys
from pathlib import Path

from hearth.core.kernel import HearthKernel, KernelConfig
from hearth.hestia.agent import HestiaAgent
from hearth.mnemosyne.memory_store import MemoryStore

# Import domain services
from hearth.domains.hermes.service import HermesService
from hearth.domains.hephaestus.service import HephaestusService
from hearth.domains.apollo.service import ApolloService
from hearth.domains.dionysus.service import DionysusService

from hearth.shared.logging.structured_logger import StructuredLogger


class HearthApplication:
    """
    Main application with domain intelligence modules.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.logger = StructuredLogger(__name__)
        self.config_path = Path(config_path or "./config/default.yaml")
        self.kernel: Optional[HearthKernel] = None
        
        self.logger.info(
            "HEARTH application with domains initializing",
            config_path=str(self.config_path)
        )
    
    def load_configuration(self) -> KernelConfig:
        """Load configuration from file."""
        # TODO: Implement YAML configuration loading
        config = KernelConfig(
            data_dir="./data",
            log_level="INFO",
            enable_audit=True,
            require_permissions=True
        )
        
        self.logger.debug("Configuration loaded", config=config.__dict__)
        return config
    
    def initialize_services(self, kernel: HearthKernel) -> None:
        """Initialize and register all services including domains."""
        self.logger.info("Initializing services with domains")
        
        # Core services
        memory_store = MemoryStore(
            db_path="./data/memory.db",
            encryption_key=None  # TODO: Load from config
        )
        
        hestia_agent = HestiaAgent()
        
        # Domain services
        hermes_service = HermesService()
        hephaestus_service = HephaestusService()
        apollo_service = ApolloService()
        dionysus_service = DionysusService()
        
        # Register services with kernel
        asyncio.run(kernel.register_service(memory_store))
        asyncio.run(kernel.register_service(hestia_agent))
        
        # Register domain services
        asyncio.run(kernel.register_service(hermes_service))
        asyncio.run(kernel.register_service(hephaestus_service))
        asyncio.run(kernel.register_service(apollo_service))
        asyncio.run(kernel.register_service(dionysus_service))
        
        self.logger.info(
            "Services initialized",
            core_services=2,
            domain_services=4
        )
    
    async def run(self) -> int:
        """Run the HEARTH application with domains."""
        try:
            # Load configuration
            config = self.load_configuration()
            
            # Initialize kernel
            self.kernel = HearthKernel(config)
            
            # Initialize services
            self.initialize_services(self.kernel)
            
            # Start kernel
            self.logger.info("Starting HEARTH kernel with domains")
            await self.kernel.start()
            
            # Main loop
            self.logger.info("HEARTH with domains is running")
            
            # Keep the application running
            while self.kernel.running:
                await asyncio.sleep(1)
            
            return 0
            
        except KeyboardInterrupt:
            self.logger.info("Shutdown requested by user")
            return 0
        except Exception as e:
            self.logger.critical(
                "Fatal error in HEARTH application",
                error=str(e),
                exc_info=True
            )
            return 1
        finally:
            await self.shutdown()
    
    async def shutdown(self) -> None:
        """Shutdown the application gracefully."""
        self.logger.info("Shutting down HEARTH application with domains")
        
        if self.kernel:
            await self.kernel.shutdown()
        
        self.logger.info("HEARTH shutdown complete")
    
    def run_sync(self) -> int:
        """Synchronous entry point."""
        return asyncio.run(self.run())


def main() -> int:
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="HEARTH Personal Cognitive OS with Domains")
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default="./config/default.yaml",
        help="Configuration file path"
    )
    parser.add_argument(
        "--list-domains",
        action="store_true",
        help="List available domain capabilities"
    )
    parser.add_argument(
        "--test-domain",
        type=str,
        help="Test a specific domain capability"
    )
    
    args = parser.parse_args()
    
    # List domains if requested
    if args.list_domains:
        print("Available Domain Capabilities:")
        print("=" * 60)
        
        # Define domain capabilities
        domains = {
            "Hermes (Communication)": [
                "draft_message - Draft messages for various contexts",
                "analyze_tone - Analyze communication tone and clarity",
                "schedule_planning - Plan schedules and meetings",
                "conversation_analysis - Analyze conversation patterns"
            ],
            "Hephaestus (Engineering)": [
                "code_analysis - Analyze code structure and complexity",
                "system_design - Reason about system architecture",
                "debug_assistance - Provide debugging strategies",
                "tech_stack_planning - Plan technology stacks"
            ],
            "Apollo (Health & Well-being)": [
                "habit_analysis - Analyze habits and routines",
                "health_pattern_modeling - Model health patterns",
                "routine_planning - Plan daily routines",
                "risk_flagging - Flag potential health risks"
            ],
            "Dionysus (Music & Recreation)": [
                "mood_analysis - Analyze mood for recommendations",
                "music_recommendation - Recommend music based on context",
                "leisure_planning - Plan leisure activities",
                "creativity_prompts - Generate creative prompts"
            ]
        }
        
        for domain, capabilities in domains.items():
            print(f"\n{domain}:")
            for capability in capabilities:
                print(f"  • {capability}")
        
        return 0
    
    # Test domain if requested
    if args.test_domain:
        print(f"Testing domain capability: {args.test_domain}")
        # TODO: Implement domain testing
        return 0
    
    # Create and run application
    app = HearthApplication(args.config)
    return app.run_sync()


if __name__ == "__main__":
    sys.exit(main())