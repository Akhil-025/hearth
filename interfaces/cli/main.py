"""
HEARTH CLI Interface - Command line interface.
"""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...core.kernel import HearthKernel, KernelConfig
from ...hestia.agent import HestiaAgent, UserInput
from ...mnemosyne.memory_store import MemoryStore
from ...shared.logging.structured_logger import StructuredLogger


console = Console()
logger = StructuredLogger(__name__)


class HearthCLI:
    """HEARTH command line interface."""
    
    def __init__(self):
        self.kernel: Optional[HearthKernel] = None
        self.agent: Optional[HestiaAgent] = None
        self.memory: Optional[MemoryStore] = None
        
        # Current session
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.user_id = "cli_user"
    
    async def initialize(self) -> bool:
        """Initialize CLI components."""
        try:
            # Create kernel
            config = KernelConfig(
                data_dir="./data",
                log_level="INFO",
                enable_audit=True
            )
            
            self.kernel = HearthKernel(config)
            
            # Initialize services
            self.memory = MemoryStore("./data/memory.db")
            self.agent = HestiaAgent()
            
            # Register services
            await self.kernel.register_service(self.memory)
            await self.kernel.register_service(self.agent)
            
            # Start kernel
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Starting HEARTH...", total=None)
                await self.kernel.start()
                progress.update(task, completed=True)
            
            console.print("[green]✓ HEARTH started successfully[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]✗ Failed to start HEARTH: {e}[/red]")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown CLI."""
        if self.kernel:
            with console.status("Shutting down..."):
                await self.kernel.shutdown()
            console.print("[yellow]HEARTH shutdown complete[/yellow]")
    
    async def chat(self, message: str) -> None:
        """Chat with Hestia."""
        if not self.agent:
            console.print("[red]Agent not initialized[/red]")
            return
        
        # Create user input
        user_input = UserInput(
            text=message,
            session_id=self.session_id,
            user_id=self.user_id
        )
        
        # Process input
        with console.status("Thinking..."):
            response = await self.agent.process_input(user_input)
        
        # Display response
        console.print(f"\n[bold cyan]Hestia:[/bold cyan] {response.text}\n")
        
        # Show actions if any
        if response.actions_executed:
            console.print("[dim]Actions executed:[/dim]")
            for action in response.actions_executed:
                console.print(f"  • {action['action']['type']}")
        
        # Show memory proposals if any
        if response.memory_proposals:
            console.print("[dim]Memory proposals:[/dim]")
            for proposal in response.memory_proposals:
                console.print(f"  • {proposal.operation} {proposal.memory_type.value}")
    
    async def ingest_document(self, file_path: Path) -> None:
        """Ingest a document into Athena."""
        from ...athena.document_ingestor import DocumentIngestor
        from ...athena.chunker import DocumentChunker, ChunkingConfig
        
        ingestor = DocumentIngestor()
        chunker = DocumentChunker(ChunkingConfig())
        
        try:
            with console.status(f"Ingesting {file_path.name}..."):
                # Ingest document
                document = await ingestor.ingest_document(file_path)
                
                # Chunk document
                chunks = chunker.chunk_document(document)
                
                # TODO: Embed and store in knowledge base
                
                console.print(f"[green]✓ Ingested {len(chunks)} chunks from {file_path.name}[/green]")
                console.print(f"  Title: {document.title}")
                console.print(f"  Content: {len(document.content)} characters")
                
        except Exception as e:
            console.print(f"[red]✗ Failed to ingest document: {e}[/red]")
    
    async def list_memories(self, category: Optional[str] = None) -> None:
        """List memories from Mnemosyne."""
        if not self.memory:
            console.print("[red]Memory store not initialized[/red]")
            return
        
        from ...shared.schemas.memory import MemoryQuery, MemoryType
        
        query = MemoryQuery(
            user_id=self.user_id,
            memory_type=MemoryType.STRUCTURED,
            category=category,
            limit=20
        )
        
        with console.status("Fetching memories..."):
            memories = await self.memory.query_memories(query)
        
        # Display as table
        table = Table(title=f"Memories ({category or 'all'})")
        table.add_column("ID", style="dim")
        table.add_column("Key")
        table.add_column("Value Preview")
        table.add_column("Confidence")
        table.add_column("Created")
        
        for memory in memories:
            value_preview = str(memory.value)[:50]
            if len(str(memory.value)) > 50:
                value_preview += "..."
            
            table.add_row(
                str(memory.memory_id)[:8],
                memory.key,
                value_preview,
                f"{memory.confidence:.2f}",
                memory.created_at.strftime("%Y-%m-%d")
            )
        
        console.print(table)
    
    async def system_status(self) -> None:
        """Display system status."""
        if not self.kernel:
            console.print("[red]Kernel not initialized[/red]")
            return
        
        status = self.kernel.get_kernel_status()
        
        table = Table(title="HEARTH System Status")
        table.add_column("Service", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Healthy", justify="center")
        table.add_column("Version")
        
        for service_name, service_status in status["services"].items():
            status_text = service_status["status"]
            healthy = "✓" if service_status["healthy"] else "✗"
            
            # Color code status
            if status_text == "running":
                status_style = "green"
            elif status_text == "error":
                status_style = "red"
            else:
                status_style = "yellow"
            
            table.add_row(
                service_name,
                f"[{status_style}]{status_text}[/{status_style}]",
                healthy,
                service_status.get("version", "N/A")
            )
        
        console.print(table)
    
    async def backup_system(self, backup_dir: Path) -> None:
        """Create system backup."""
        import shutil
        import sqlite3
        
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        with console.status("Creating backup..."):
            # Backup database
            db_path = Path("./data/memory.db")
            if db_path.exists():
                backup_db = backup_dir / f"memory_{timestamp}.db"
                shutil.copy2(db_path, backup_db)
            
            # Backup configuration
            config_path = Path("./config")
            if config_path.exists():
                backup_config = backup_dir / f"config_{timestamp}"
                shutil.copytree(config_path, backup_config)
            
            # Create manifest
            manifest = {
                "timestamp": timestamp,
                "version": "0.1.0",
                "backup_files": [
                    str(p.relative_to(backup_dir))
                    for p in backup_dir.glob("**/*") if p.is_file()
                ]
            }
            
            manifest_path = backup_dir / "manifest.json"
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)
        
        console.print(f"[green]✓ Backup created at {backup_dir}[/green]")


@click.group()
@click.pass_context
def hearth_cli(ctx):
    """HEARTH - Personal Cognitive Operating System"""
    ctx.ensure_object(dict)
    ctx.obj['cli'] = HearthCLI()


@hearth_cli.command()
@click.pass_context
def status(ctx):
    """Show system status."""
    cli = ctx.obj['cli']
    asyncio.run(cli.system_status())


@hearth_cli.command()
@click.argument('message')
@click.pass_context
def chat(ctx, message):
    """Chat with Hestia."""
    cli = ctx.obj['cli']
    
    async def run():
        if not cli.kernel:
            await cli.initialize()
        await cli.chat(message)
    
    asyncio.run(run())


@hearth_cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.pass_context
def ingest(ctx, file_path):
    """Ingest a document."""
    cli = ctx.obj['cli']
    
    async def run():
        if not cli.kernel:
            await cli.initialize()
        await cli.ingest_document(Path(file_path))
    
    asyncio.run(run())


@hearth_cli.command()
@click.option('--category', help='Filter by category')
@click.pass_context
def memories(ctx, category):
    """List memories."""
    cli = ctx.obj['cli']
    
    async def run():
        if not cli.kernel:
            await cli.initialize()
        await cli.list_memories(category)
    
    asyncio.run(run())


@hearth_cli.command()
@click.argument('backup_dir', type=click.Path())
@click.pass_context
def backup(ctx, backup_dir):
    """Create system backup."""
    cli = ctx.obj['cli']
    
    async def run():
        await cli.backup_system(Path(backup_dir))
    
    asyncio.run(run())


@hearth_cli.command()
@click.pass_context
def shell(ctx):
    """Interactive shell."""
    cli = ctx.obj['cli']
    
    async def run():
        if not cli.kernel:
            await cli.initialize()
        
        console.print("[bold cyan]HEARTH Interactive Shell[/bold cyan]")
        console.print("Type 'quit' or 'exit' to leave\n")
        
        while True:
            try:
                message = click.prompt("[you]", prompt_suffix="> ")
                
                if message.lower() in ['quit', 'exit', 'q']:
                    break
                
                await cli.chat(message)
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted[/yellow]")
                break
            except EOFError:
                break
        
        await cli.shutdown()
    
    asyncio.run(run())


if __name__ == "__main__":
    hearth_cli()