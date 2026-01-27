"""
Complete HEARTH System Example
Demonstrates integration of all components.
"""
import asyncio
from datetime import datetime
from pathlib import Path
from uuid import uuid4


async def complete_hearth_example():
    """Complete example demonstrating all HEARTH components."""
    print("🚀 HEARTH Complete System Example")
    print("=" * 60)
    
    # 1. Initialize Kernel
    print("\n1. Initializing HEARTH Kernel...")
    from hearth.core.kernel import HearthKernel, KernelConfig
    
    config = KernelConfig(
        data_dir="./example_data",
        log_level="INFO",
        enable_audit=True
    )
    
    kernel = HearthKernel(config)
    
    # 2. Initialize and Register Services
    print("2. Initializing Services...")
    
    # Memory Store
    from hearth.mnemosyne.memory_store import MemoryStore
    memory_store = MemoryStore("./example_data/memory.db")
    
    # Hestia Agent
    from hearth.hestia.agent import HestiaAgent
    hestia_agent = HestiaAgent()
    
    # Athena Knowledge Engine
    from hearth.athena.document_ingestor import DocumentIngestor
    from hearth.athena.chunker import DocumentChunker, ChunkingConfig
    from hearth.athena.embedder import Embedder
    from hearth.athena.knowledge_store import KnowledgeStore
    
    document_ingestor = DocumentIngestor()
    chunker = DocumentChunker(ChunkingConfig())
    embedder = Embedder()
    knowledge_store = KnowledgeStore()
    
    # Pluto Financial System
    from hearth.pluto.ledger import Ledger
    from hearth.pluto.normalizer import TransactionNormalizer
    from hearth.pluto.budget_engine import BudgetEngine
    
    ledger = Ledger("./example_data/ledger.db")
    normalizer = TransactionNormalizer()
    budget_engine = BudgetEngine()
    
    # Register all services
    await kernel.register_service(memory_store)
    await kernel.register_service(hestia_agent)
    await kernel.register_service(document_ingestor)
    await kernel.register_service(knowledge_store)
    await kernel.register_service(ledger)
    
    # 3. Start the System
    print("3. Starting HEARTH System...")
    await kernel.start()
    
    print("✅ HEARTH System Started Successfully")
    print("-" * 60)
    
    # 4. Demonstrate Memory Operations
    print("\n4. Memory Operations (Mnemosyne):")
    
    # Store a memory
    from hearth.shared.schemas.memory import StructuredMemory, MemoryType
    from hearth.mnemosyne.memory_store import MemoryQuery
    
    memory = StructuredMemory(
        user_id="example_user",
        memory_type=MemoryType.STRUCTURED,
        category="preferences",
        key="favorite_coffee",
        value="oat milk latte",
        tags=["coffee", "preference", "morning"]
    )
    
    await memory_store.store_structured_memory(memory)
    print("   ✓ Stored memory: favorite_coffee = oat milk latte")
    
    # Query memories
    query = MemoryQuery(
        user_id="example_user",
        category="preferences"
    )
    
    memories = await memory_store.query_memories(query)
    print(f"   ✓ Retrieved {len(memories)} memory(ies)")
    
    # 5. Demonstrate Hestia Interaction
    print("\n5. Agent Interaction (Hestia):")
    
    from hearth.hestia.agent import UserInput
    
    user_input = UserInput(
        text="Remember that I like oat milk latte for coffee",
        session_id="example_session",
        user_id="example_user"
    )
    
    response = await hestia_agent.process_input(user_input)
    print(f"   ✓ Agent response: {response.text[:50]}...")
    print(f"   ✓ Generated {len(response.memory_proposals)} memory proposal(s)")
    
    # 6. Demonstrate Knowledge Ingestion
    print("\n6. Knowledge Ingestion (Athena):")
    
    # Create a test document
    test_doc = Path("./example_data/test_document.txt")
    test_doc.parent.mkdir(exist_ok=True)
    test_doc.write_text("HEARTH is a personal cognitive operating system. "
                       "It helps you organize thoughts, memories, and knowledge.")
    
    # Ingest document
    document = await document_ingestor.ingest_document(test_doc)
    print(f"   ✓ Ingested document: {document.title}")
    print(f"   ✓ Content length: {len(document.content)} characters")
    
    # Chunk document
    chunks = chunker.chunk_document(document)
    print(f"   ✓ Created {len(chunks)} chunk(s)")
    
    # Embed chunks
    embedded_chunks = await embedder.embed_chunks(chunks[:3])  # Just first 3 for speed
    print(f"   ✓ Embedded {len(embedded_chunks)} chunk(s)")
    
    # 7. Demonstrate Financial Operations
    print("\n7. Financial Operations (Pluto):")
    
    from hearth.shared.schemas.finance import (
        Account, AccountType, Currency, Transaction, TransactionType
    )
    
    # Create accounts
    checking_account = Account(
        account_id=uuid4(),
        user_id="example_user",
        account_type=AccountType.ASSET_CURRENT,
        name="Checking Account",
        currency=Currency.USD,
        opening_balance=1000.00
    )
    
    grocery_account = Account(
        account_id=uuid4(),
        user_id="example_user",
        account_type=AccountType.EXPENSE_OPERATING,
        name="Groceries",
        currency=Currency.USD
    )
    
    await ledger.create_account(checking_account)
    await ledger.create_account(grocery_account)
    print("   ✓ Created accounts: Checking, Groceries")
    
    # Record a transaction
    transaction = Transaction(
        transaction_id=uuid4(),
        user_id="example_user",
        transaction_type=TransactionType.EXPENSE,
        description="Grocery shopping",
        amount=75.50,
        currency=Currency.USD,
        from_account_id=checking_account.account_id,
        to_account_id=grocery_account.account_id
    )
    
    success, error = await ledger.record_transaction(transaction)
    if success:
        print("   ✓ Recorded transaction: Grocery shopping $75.50")
    else:
        print(f"   ✗ Failed to record transaction: {error}")
    
    # Generate balance sheet
    balance_sheet = await ledger.generate_balance_sheet()
    print(f"   ✓ Generated balance sheet")
    print(f"     Total Assets: ${balance_sheet.total_assets}")
    print(f"     Total Liabilities: ${balance_sheet.total_liabilities}")
    print(f"     Equity: ${balance_sheet.equity}")
    
    # 8. System Status
    print("\n8. System Status:")
    
    status = kernel.get_kernel_status()
    running_services = sum(
        1 for s in status["services"].values()
        if s["status"] == "running" and s["healthy"]
    )
    
    print(f"   ✓ Running services: {running_services}/{len(status['services'])}")
    print(f"   ✓ System uptime: {status.get('uptime_seconds', 0):.1f} seconds")
    
    # 9. Cleanup
    print("\n9. System Shutdown...")
    await kernel.shutdown()
    
    # Cleanup test files
    import shutil
    if Path("./example_data").exists():
        shutil.rmtree("./example_data")
    
    print("✅ Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(complete_hearth_example())