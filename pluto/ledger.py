"""
Financial Ledger - Double-entry accounting with encryption.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator

from ..core.kernel import IService, ServiceInfo, ServiceStatus
from ..shared.crypto.encryption import encrypt_data, decrypt_data
from ..shared.logging.structured_logger import StructuredLogger
from ..shared.schemas.finance import (
    Account,
    AccountType,
    Currency,
    Transaction,
    TransactionStatus,
    TransactionType
)


class LedgerEntry(BaseModel):
    """Double-entry ledger entry."""
    entry_id: UUID = Field(default_factory=uuid4)
    transaction_id: UUID
    account_id: UUID
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Amounts (positive for debit, negative for credit in asset accounts)
    amount: Decimal
    currency: Currency
    
    # Description
    description: str
    reference: Optional[str] = None
    
    # Reconciliation
    reconciled: bool = False
    reconciled_at: Optional[datetime] = None
    reconciled_by: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    
    @validator('amount')
    def validate_amount(cls, v):
        """Validate amount precision."""
        return v.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


class BalanceSheet(BaseModel):
    """Balance sheet snapshot."""
    snapshot_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Assets
    current_assets: Decimal = Decimal('0.00')
    fixed_assets: Decimal = Decimal('0.00')
    total_assets: Decimal = Decimal('0.00')
    
    # Liabilities
    current_liabilities: Decimal = Decimal('0.00')
    long_term_liabilities: Decimal = Decimal('0.00')
    total_liabilities: Decimal = Decimal('0.00')
    
    # Equity
    equity: Decimal = Decimal('0.00')
    
    # Validation
    balance_check: bool = False
    
    @validator('balance_check', always=True)
    def check_balance(cls, v, values):
        """Check accounting equation: Assets = Liabilities + Equity."""
        assets = values.get('total_assets', Decimal('0.00'))
        liabilities = values.get('total_liabilities', Decimal('0.00'))
        equity = values.get('equity', Decimal('0.00'))
        
        diff = abs(assets - (liabilities + equity))
        return diff < Decimal('0.01')  # Allow small rounding differences


class IncomeStatement(BaseModel):
    """Income statement for a period."""
    statement_id: UUID = Field(default_factory=uuid4)
    start_date: datetime
    end_date: datetime
    generated_at: datetime = Field(default_factory=datetime.now)
    
    # Revenue
    revenue: Decimal = Decimal('0.00')
    
    # Expenses
    cost_of_goods_sold: Decimal = Decimal('0.00')
    operating_expenses: Decimal = Decimal('0.00')
    interest_expense: Decimal = Decimal('0.00')
    taxes: Decimal = Decimal('0.00')
    total_expenses: Decimal = Decimal('0.00')
    
    # Profit
    gross_profit: Decimal = Decimal('0.00')
    operating_profit: Decimal = Decimal('0.00')
    net_profit: Decimal = Decimal('0.00')
    
    # Metadata
    currency: Currency = Currency.USD


class LedgerQuery(BaseModel):
    """Ledger query parameters."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    account_ids: Optional[List[UUID]] = None
    transaction_ids: Optional[List[UUID]] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    reconciled_only: bool = False
    unreconciled_only: bool = False
    limit: int = 1000
    offset: int = 0


class Ledger(IService):
    """
    Double-entry accounting ledger with encryption.
    
    Features:
    - Double-entry bookkeeping
    - Transaction validation
    - Account reconciliation
    - Financial reporting
    - Audit trails
    """
    
    def __init__(
        self,
        db_path: Optional[str] = None,
        encryption_key: Optional[str] = None
    ):
        self.db_path = db_path or "./data/ledger.db"
        self.encryption_key = encryption_key
        self.logger = StructuredLogger(__name__)
        
        # Database connection
        self.conn = None
        
        # Account cache
        self.accounts: Dict[UUID, Account] = {}
        self.account_tree: Dict[UUID, List[UUID]] = {}  # parent -> children
        
        # Service info
        self.service_info = ServiceInfo(
            name="pluto_ledger",
            version="0.1.0",
            dependencies=[]
        )
        
        self.logger.info("Financial ledger initialized")
    
    async def start(self) -> None:
        """Start ledger service."""
        self.service_info.status = ServiceStatus.STARTING
        
        # Initialize database
        await self._initialize_database()
        
        # Load accounts
        await self._load_accounts()
        
        self.service_info.status = ServiceStatus.RUNNING
        self.logger.info(
            "Financial ledger started",
            account_count=len(self.accounts)
        )
    
    async def stop(self) -> None:
        """Stop ledger service."""
        self.service_info.status = ServiceStatus.STOPPING
        
        if self.conn:
            self.conn.close()
            self.conn = None
        
        self.accounts.clear()
        self.account_tree.clear()
        
        self.service_info.status = ServiceStatus.STOPPED
        self.logger.info("Financial ledger stopped")
    
    def get_service_info(self) -> ServiceInfo:
        """Get service metadata."""
        return self.service_info
    
    async def health_check(self) -> bool:
        """Check ledger health."""
        try:
            # Check database connection
            if not self.conn:
                return False
            
            # Check basic accounting equation
            await self.validate_ledger()
            return True
            
        except Exception as e:
            self.logger.error("Ledger health check failed", error=str(e))
            return False
    
    async def _initialize_database(self) -> None:
        """Initialize ledger database schema."""
        import aiosqlite
        
        self.conn = await aiosqlite.connect(self.db_path)
        
        # Enable foreign keys
        await self.conn.execute("PRAGMA foreign_keys = ON")
        await self.conn.execute("PRAGMA journal_mode = WAL")
        
        # Create tables
        await self.conn.executescript("""
            -- Accounts table
            CREATE TABLE IF NOT EXISTS accounts (
                account_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                account_type TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                parent_account_id TEXT,
                currency TEXT NOT NULL,
                opening_balance DECIMAL(15, 2) DEFAULT 0.00,
                current_balance DECIMAL(15, 2) DEFAULT 0.00,
                is_active BOOLEAN DEFAULT TRUE,
                metadata_encrypted TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (parent_account_id) REFERENCES accounts(account_id),
                UNIQUE(user_id, account_type, name)
            );
            
            -- Transactions table
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                description TEXT NOT NULL,
                reference TEXT,
                amount DECIMAL(15, 2) NOT NULL,
                currency TEXT NOT NULL,
                transaction_date TIMESTAMP NOT NULL,
                value_date TIMESTAMP,
                status TEXT DEFAULT 'pending',
                category TEXT,
                tags_encrypted TEXT,
                metadata_encrypted TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CHECK (amount > 0)
            );
            
            -- Ledger entries table (double-entry)
            CREATE TABLE IF NOT EXISTS ledger_entries (
                entry_id TEXT PRIMARY KEY,
                transaction_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                amount DECIMAL(15, 2) NOT NULL,
                currency TEXT NOT NULL,
                description TEXT NOT NULL,
                reference TEXT,
                reconciled BOOLEAN DEFAULT FALSE,
                reconciled_at TIMESTAMP,
                reconciled_by TEXT,
                metadata_encrypted TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id),
                FOREIGN KEY (account_id) REFERENCES accounts(account_id)
            );
            
            -- Audit trail
            CREATE TABLE IF NOT EXISTS ledger_audit (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                old_value_encrypted TEXT,
                new_value_encrypted TEXT,
                performed_by TEXT NOT NULL,
                performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reason TEXT
            );
            
            -- Indexes for performance
            CREATE INDEX IF NOT EXISTS idx_ledger_account ON ledger_entries(account_id);
            CREATE INDEX IF NOT EXISTS idx_ledger_transaction ON ledger_entries(transaction_id);
            CREATE INDEX IF NOT EXISTS idx_ledger_timestamp ON ledger_entries(timestamp);
            CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(transaction_date);
            CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id);
        """)
        
        await self.conn.commit()
        
        self.logger.debug("Ledger database initialized")
    
    async def _load_accounts(self) -> None:
        """Load accounts from database."""
        async with self.conn.execute("SELECT metadata_encrypted FROM accounts") as cursor:
            rows = await cursor.fetchall()
            
            for row in rows:
                encrypted_data = row[0]
                if encrypted_data and self.encryption_key:
                    account_data = json.loads(decrypt_data(encrypted_data, self.encryption_key))
                    account = Account(**account_data)
                    self.accounts[account.account_id] = account
                    
                    # Build tree
                    if account.parent_account_id:
                        if account.parent_account_id not in self.account_tree:
                            self.account_tree[account.parent_account_id] = []
                        self.account_tree[account.parent_account_id].append(account.account_id)
    
    async def create_account(self, account: Account) -> bool:
        """Create a new account."""
        try:
            # Encrypt metadata
            metadata_json = account.json()
            encrypted_metadata = (
                encrypt_data(metadata_json, self.encryption_key)
                if self.encryption_key else metadata_json
            )
            
            # Insert account
            await self.conn.execute("""
                INSERT INTO accounts (
                    account_id, user_id, account_type, name, description,
                    parent_account_id, currency, opening_balance, current_balance,
                    is_active, metadata_encrypted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(account.account_id),
                account.user_id,
                account.account_type.value,
                account.name,
                account.description,
                str(account.parent_account_id) if account.parent_account_id else None,
                account.currency.value,
                str(account.opening_balance),
                str(account.current_balance),
                account.is_active,
                encrypted_metadata
            ))
            
            await self.conn.commit()
            
            # Update cache
            self.accounts[account.account_id] = account
            if account.parent_account_id:
                if account.parent_account_id not in self.account_tree:
                    self.account_tree[account.parent_account_id] = []
                self.account_tree[account.parent_account_id].append(account.account_id)
            
            self.logger.info(
                "Account created",
                account_id=str(account.account_id),
                name=account.name,
                type=account.account_type.value
            )
            
            # Audit trail
            await self._audit_event(
                event_type="CREATE",
                entity_type="ACCOUNT",
                entity_id=str(account.account_id),
                new_value=account.dict(),
                performed_by="system"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to create account",
                error=str(e),
                account_name=account.name
            )
            return False
    
    async def record_transaction(self, transaction: Transaction) -> Tuple[bool, str]:
        """
        Record a transaction with double-entry bookkeeping.
        
        Returns: (success, error_message)
        """
        # Validate transaction
        validation_error = await self._validate_transaction(transaction)
        if validation_error:
            return False, validation_error
        
        try:
            # Start transaction
            await self.conn.execute("BEGIN")
            
            # Encrypt transaction metadata
            transaction_json = transaction.json()
            encrypted_metadata = (
                encrypt_data(transaction_json, self.encryption_key)
                if self.encryption_key else transaction_json
            )
            
            encrypted_tags = (
                encrypt_data(json.dumps(transaction.tags), self.encryption_key)
                if self.encryption_key and transaction.tags else json.dumps(transaction.tags or [])
            )
            
            # Insert transaction
            await self.conn.execute("""
                INSERT INTO transactions (
                    transaction_id, user_id, transaction_type, description,
                    reference, amount, currency, transaction_date, value_date,
                    status, category, tags_encrypted, metadata_encrypted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(transaction.transaction_id),
                transaction.user_id,
                transaction.transaction_type.value,
                transaction.description,
                transaction.reference,
                str(transaction.amount),
                transaction.currency.value,
                transaction.transaction_date.isoformat(),
                transaction.value_date.isoformat() if transaction.value_date else None,
                transaction.status.value,
                transaction.category,
                encrypted_tags,
                encrypted_metadata
            ))
            
            # Create ledger entries based on transaction type
            entries = await self._create_ledger_entries(transaction)
            
            # Insert ledger entries
            for entry in entries:
                entry_metadata = entry.json()
                encrypted_entry_metadata = (
                    encrypt_data(entry_metadata, self.encryption_key)
                    if self.encryption_key else entry_metadata
                )
                
                await self.conn.execute("""
                    INSERT INTO ledger_entries (
                        entry_id, transaction_id, account_id, amount,
                        currency, description, reference, metadata_encrypted
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(entry.entry_id),
                    str(entry.transaction_id),
                    str(entry.account_id),
                    str(entry.amount),
                    entry.currency.value,
                    entry.description,
                    entry.reference,
                    encrypted_entry_metadata
                ))
                
                # Update account balance
                await self._update_account_balance(entry.account_id, entry.amount)
            
            # Commit transaction
            await self.conn.execute("COMMIT")
            
            self.logger.info(
                "Transaction recorded",
                transaction_id=str(transaction.transaction_id),
                amount=str(transaction.amount),
                type=transaction.transaction_type.value
            )
            
            # Audit trail
            await self._audit_event(
                event_type="CREATE",
                entity_type="TRANSACTION",
                entity_id=str(transaction.transaction_id),
                new_value=transaction.dict(),
                performed_by="system"
            )
            
            return True, ""
            
        except Exception as e:
            # Rollback on error
            await self.conn.execute("ROLLBACK")
            
            self.logger.error(
                "Failed to record transaction",
                error=str(e),
                transaction_id=str(transaction.transaction_id)
            )
            
            return False, str(e)
    
    async def _validate_transaction(self, transaction: Transaction) -> Optional[str]:
        """Validate transaction before recording."""
        # Check accounts exist
        for account_id in [transaction.from_account_id, transaction.to_account_id]:
            if account_id and account_id not in self.accounts:
                return f"Account not found: {account_id}"
        
        # Check amount
        if transaction.amount <= Decimal('0.00'):
            return "Amount must be positive"
        
        # Check currency matches accounts
        from_account = self.accounts.get(transaction.from_account_id)
        to_account = self.accounts.get(transaction.to_account_id)
        
        if from_account and from_account.currency != transaction.currency:
            return f"Currency mismatch for from account: {from_account.currency} != {transaction.currency}"
        
        if to_account and to_account.currency != transaction.currency:
            return f"Currency mismatch for to account: {to_account.currency} != {transaction.currency}"
        
        return None
    
    async def _create_ledger_entries(self, transaction: Transaction) -> List[LedgerEntry]:
        """Create double-entry ledger entries for transaction."""
        entries = []
        
        # Determine debit/credit based on account types and transaction type
        from_account = self.accounts.get(transaction.from_account_id)
        to_account = self.accounts.get(transaction.to_account_id)
        
        if not from_account or not to_account:
            raise ValueError("Both accounts must exist")
        
        # For asset accounts: debit increases, credit decreases
        # For liability/equity accounts: credit increases, debit decreases
        
        if transaction.transaction_type == TransactionType.TRANSFER:
            # Debit destination, credit source
            entries.append(LedgerEntry(
                transaction_id=transaction.transaction_id,
                account_id=to_account.account_id,
                amount=transaction.amount,  # Debit (positive)
                currency=transaction.currency,
                description=f"Transfer from {from_account.name}",
                reference=transaction.reference
            ))
            
            entries.append(LedgerEntry(
                transaction_id=transaction.transaction_id,
                account_id=from_account.account_id,
                amount=-transaction.amount,  # Credit (negative)
                currency=transaction.currency,
                description=f"Transfer to {to_account.name}",
                reference=transaction.reference
            ))
        
        elif transaction.transaction_type == TransactionType.EXPENSE:
            # Debit expense, credit asset
            entries.append(LedgerEntry(
                transaction_id=transaction.transaction_id,
                account_id=to_account.account_id,  # Expense account
                amount=transaction.amount,  # Debit (positive)
                currency=transaction.currency,
                description=transaction.description,
                reference=transaction.reference
            ))
            
            entries.append(LedgerEntry(
                transaction_id=transaction.transaction_id,
                account_id=from_account.account_id,  # Asset account
                amount=-transaction.amount,  # Credit (negative)
                currency=transaction.currency,
                description=transaction.description,
                reference=transaction.reference
            ))
        
        elif transaction.transaction_type == TransactionType.INCOME:
            # Credit income, debit asset
            entries.append(LedgerEntry(
                transaction_id=transaction.transaction_id,
                account_id=to_account.account_id,  # Asset account
                amount=transaction.amount,  # Debit (positive)
                currency=transaction.currency,
                description=transaction.description,
                reference=transaction.reference
            ))
            
            entries.append(LedgerEntry(
                transaction_id=transaction.transaction_id,
                account_id=from_account.account_id,  # Income account
                amount=-transaction.amount,  # Credit (negative)
                currency=transaction.currency,
                description=transaction.description,
                reference=transaction.reference
            ))
        
        return entries
    
    async def _update_account_balance(self, account_id: UUID, amount: Decimal) -> None:
        """Update account balance."""
        await self.conn.execute("""
            UPDATE accounts
            SET current_balance = current_balance + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE account_id = ?
        """, (str(amount), str(account_id)))
        
        # Update cache
        if account_id in self.accounts:
            self.accounts[account_id].current_balance += amount
    
    async def get_account_balance(self, account_id: UUID) -> Decimal:
        """Get current balance for account."""
        if account_id in self.accounts:
            return self.accounts[account_id].current_balance
        
        async with self.conn.execute("""
            SELECT current_balance FROM accounts WHERE account_id = ?
        """, (str(account_id),)) as cursor:
            row = await cursor.fetchone()
            if row:
                return Decimal(row[0])
        
        return Decimal('0.00')
    
    async def query_ledger(self, query: LedgerQuery) -> List[LedgerEntry]:
        """Query ledger entries."""
        # Build SQL query
        sql = """
            SELECT metadata_encrypted FROM ledger_entries
            WHERE 1=1
        """
        params = []
        
        if query.start_date:
            sql += " AND timestamp >= ?"
            params.append(query.start_date.isoformat())
        
        if query.end_date:
            sql += " AND timestamp <= ?"
            params.append(query.end_date.isoformat())
        
        if query.account_ids:
            placeholders = ','.join(['?' for _ in query.account_ids])
            sql += f" AND account_id IN ({placeholders})"
            params.extend([str(id) for id in query.account_ids])
        
        if query.transaction_ids:
            placeholders = ','.join(['?' for _ in query.transaction_ids])
            sql += f" AND transaction_id IN ({placeholders})"
            params.extend([str(id) for id in query.transaction_ids])
        
        if query.reconciled_only:
            sql += " AND reconciled = TRUE"
        
        if query.unreconciled_only:
            sql += " AND reconciled = FALSE"
        
        # Order and limit
        sql += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([query.limit, query.offset])
        
        # Execute query
        entries = []
        async with self.conn.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
            
            for row in rows:
                encrypted_data = row[0]
                if encrypted_data and self.encryption_key:
                    entry_data = json.loads(decrypt_data(encrypted_data, self.encryption_key))
                    entries.append(LedgerEntry(**entry_data))
        
        return entries
    
    async def reconcile_entry(
        self,
        entry_id: UUID,
        reconciled_by: str,
        notes: Optional[str] = None
    ) -> bool:
        """Reconcile a ledger entry."""
        try:
            await self.conn.execute("""
                UPDATE ledger_entries
                SET reconciled = TRUE,
                    reconciled_at = CURRENT_TIMESTAMP,
                    reconciled_by = ?
                WHERE entry_id = ?
            """, (reconciled_by, str(entry_id)))
            
            await self.conn.commit()
            
            self.logger.info(
                "Ledger entry reconciled",
                entry_id=str(entry_id),
                reconciled_by=reconciled_by
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to reconcile entry",
                error=str(e),
                entry_id=str(entry_id)
            )
            return False
    
    async def generate_balance_sheet(self, as_of: Optional[datetime] = None) -> BalanceSheet:
        """Generate balance sheet as of specific date."""
        if not as_of:
            as_of = datetime.now()
        
        balance_sheet = BalanceSheet(timestamp=as_of)
        
        # Calculate account balances
        async with self.conn.execute("""
            SELECT 
                a.account_type,
                SUM(
                    CASE WHEN le.timestamp <= ? 
                    THEN le.amount ELSE 0 END
                ) as balance
            FROM accounts a
            LEFT JOIN ledger_entries le ON a.account_id = le.account_id
            WHERE a.is_active = TRUE
            GROUP BY a.account_type
        """, (as_of.isoformat(),)) as cursor:
            rows = await cursor.fetchall()
            
            for account_type, balance in rows:
                balance_decimal = Decimal(balance or '0.00')
                
                if account_type == AccountType.ASSET_CURRENT.value:
                    balance_sheet.current_assets = balance_decimal
                elif account_type == AccountType.ASSET_FIXED.value:
                    balance_sheet.fixed_assets = balance_decimal
                elif account_type == AccountType.LIABILITY_CURRENT.value:
                    balance_sheet.current_liabilities = balance_decimal
                elif account_type == AccountType.LIABILITY_LONG_TERM.value:
                    balance_sheet.long_term_liabilities = balance_decimal
                elif account_type == AccountType.EQUITY.value:
                    balance_sheet.equity = balance_decimal
        
        # Calculate totals
        balance_sheet.total_assets = (
            balance_sheet.current_assets + 
            balance_sheet.fixed_assets
        )
        
        balance_sheet.total_liabilities = (
            balance_sheet.current_liabilities + 
            balance_sheet.long_term_liabilities
        )
        
        return balance_sheet
    
    async def generate_income_statement(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> IncomeStatement:
        """Generate income statement for period."""
        statement = IncomeStatement(
            start_date=start_date,
            end_date=end_date
        )
        
        # Calculate revenue (income accounts)
        async with self.conn.execute("""
            SELECT SUM(le.amount) as revenue
            FROM ledger_entries le
            JOIN accounts a ON le.account_id = a.account_id
            WHERE a.account_type IN (?, ?)
            AND le.timestamp BETWEEN ? AND ?
        """, (
            AccountType.INCOME.value,
            AccountType.INCOME_OTHER.value,
            start_date.isoformat(),
            end_date.isoformat()
        )) as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                # Income is credited (negative in our system), so invert
                statement.revenue = -Decimal(row[0])
        
        # Calculate expenses (expense accounts)
        async with self.conn.execute("""
            SELECT 
                SUM(CASE WHEN a.account_type = ? THEN le.amount ELSE 0 END) as cogs,
                SUM(CASE WHEN a.account_type = ? THEN le.amount ELSE 0 END) as operating,
                SUM(CASE WHEN a.account_type = ? THEN le.amount ELSE 0 END) as interest,
                SUM(CASE WHEN a.account_type = ? THEN le.amount ELSE 0 END) as taxes
            FROM ledger_entries le
            JOIN accounts a ON le.account_id = a.account_id
            WHERE a.account_type IN (?, ?, ?, ?)
            AND le.timestamp BETWEEN ? AND ?
        """, (
            AccountType.EXPENSE_COGS.value,
            AccountType.EXPENSE_OPERATING.value,
            AccountType.EXPENSE_INTEREST.value,
            AccountType.EXPENSE_TAX.value,
            AccountType.EXPENSE_COGS.value,
            AccountType.EXPENSE_OPERATING.value,
            AccountType.EXPENSE_INTEREST.value,
            AccountType.EXPENSE_TAX.value,
            start_date.isoformat(),
            end_date.isoformat()
        )) as cursor:
            row = await cursor.fetchone()
            if row:
                # Expenses are debited (positive in our system)
                statement.cost_of_goods_sold = Decimal(row[0] or '0.00')
                statement.operating_expenses = Decimal(row[1] or '0.00')
                statement.interest_expense = Decimal(row[2] or '0.00')
                statement.taxes = Decimal(row[3] or '0.00')
        
        # Calculate totals
        statement.total_expenses = (
            statement.cost_of_goods_sold +
            statement.operating_expenses +
            statement.interest_expense +
            statement.taxes
        )
        
        statement.gross_profit = statement.revenue - statement.cost_of_goods_sold
        statement.operating_profit = statement.gross_profit - statement.operating_expenses
        statement.net_profit = (
            statement.operating_profit - 
            statement.interest_expense - 
            statement.taxes
        )
        
        return statement
    
    async def validate_ledger(self) -> Tuple[bool, List[str]]:
        """Validate ledger integrity."""
        errors = []
        
        # Check that total debits equal total credits
        async with self.conn.execute("""
            SELECT SUM(amount) FROM ledger_entries
        """) as cursor:
            row = await cursor.fetchone()
            total = Decimal(row[0] or '0.00')
            
            if abs(total) > Decimal('0.01'):  # Allow small rounding errors
                errors.append(f"Ledger out of balance: {total}")
        
        # Check account balances match sum of entries
        async with self.conn.execute("""
            SELECT 
                a.account_id,
                a.current_balance as account_balance,
                COALESCE(SUM(le.amount), 0) as entry_balance
            FROM accounts a
            LEFT JOIN ledger_entries le ON a.account_id = le.account_id
            GROUP BY a.account_id, a.current_balance
        """) as cursor:
            rows = await cursor.fetchall()
            
            for account_id, account_balance, entry_balance in rows:
                if abs(Decimal(account_balance or '0.00') - Decimal(entry_balance or '0.00')) > Decimal('0.01'):
                    errors.append(
                        f"Account {account_id} out of balance: "
                        f"account={account_balance}, entries={entry_balance}"
                    )
        
        return len(errors) == 0, errors
    
    async def _audit_event(
        self,
        event_type: str,
        entity_type: str,
        entity_id: str,
        old_value: Optional[Dict] = None,
        new_value: Optional[Dict] = None,
        performed_by: str = "system",
        reason: Optional[str] = None
    ) -> None:
        """Record audit event."""
        try:
            old_value_json = json.dumps(old_value) if old_value else None
            new_value_json = json.dumps(new_value) if new_value else None
            
            old_value_encrypted = (
                encrypt_data(old_value_json, self.encryption_key)
                if old_value_json and self.encryption_key else old_value_json
            )
            
            new_value_encrypted = (
                encrypt_data(new_value_json, self.encryption_key)
                if new_value_json and self.encryption_key else new_value_json
            )
            
            await self.conn.execute("""
                INSERT INTO ledger_audit (
                    event_type, entity_type, entity_id,
                    old_value_encrypted, new_value_encrypted,
                    performed_by, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                event_type,
                entity_type,
                entity_id,
                old_value_encrypted,
                new_value_encrypted,
                performed_by,
                reason
            ))
            
            await self.conn.commit()
            
        except Exception as e:
            self.logger.error("Failed to record audit event", error=str(e))