"""Storage backends for usage records."""

import json
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from .models import UsageRecord, Provider


class StorageBackend(ABC):
    """Abstract base class for storage backends."""
    
    @abstractmethod
    def save(self, record: UsageRecord) -> None:
        """Save a usage record."""
        pass
    
    @abstractmethod
    def get_records(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        agent: Optional[str] = None,
        task: Optional[str] = None,
        user: Optional[str] = None,
        limit: int = 1000
    ) -> List[UsageRecord]:
        """Query usage records with filters."""
        pass
    
    @abstractmethod
    def get_total_cost(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> float:
        """Get total cost in time range."""
        pass


class SQLiteStorage(StorageBackend):
    """SQLite storage backend for usage records."""
    
    def __init__(self, db_path: str = "ai_costs.db"):
        self.db_path = Path(db_path)
        self._init_db()
    
    def _init_db(self):
        """Initialize the database schema."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS usage_records (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    task TEXT NOT NULL,
                    user TEXT,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    input_cost REAL NOT NULL,
                    output_cost REAL NOT NULL,
                    total_cost REAL NOT NULL,
                    prompt_hash TEXT,
                    prompt_preview TEXT,
                    latency_ms INTEGER
                )
            """)
            
            # Create indexes for common queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON usage_records(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_agent ON usage_records(agent)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_task ON usage_records(task)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user ON usage_records(user)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_prompt_hash ON usage_records(prompt_hash)")
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection with context management."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def save(self, record: UsageRecord) -> None:
        """Save a usage record."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO usage_records 
                (id, timestamp, agent, task, user, provider, model,
                 input_tokens, output_tokens, total_tokens,
                 input_cost, output_cost, total_cost,
                 prompt_hash, prompt_preview, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.id,
                record.timestamp.isoformat(),
                record.agent,
                record.task,
                record.user,
                record.provider.value,
                record.model,
                record.input_tokens,
                record.output_tokens,
                record.total_tokens,
                record.input_cost,
                record.output_cost,
                record.total_cost,
                record.prompt_hash,
                record.prompt_preview,
                record.latency_ms
            ))
            conn.commit()
    
    def _row_to_record(self, row: sqlite3.Row) -> UsageRecord:
        """Convert a database row to a UsageRecord."""
        return UsageRecord(
            id=row["id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            agent=row["agent"],
            task=row["task"],
            user=row["user"],
            provider=Provider(row["provider"]),
            model=row["model"],
            input_tokens=row["input_tokens"],
            output_tokens=row["output_tokens"],
            total_tokens=row["total_tokens"],
            input_cost=row["input_cost"],
            output_cost=row["output_cost"],
            total_cost=row["total_cost"],
            prompt_hash=row["prompt_hash"],
            prompt_preview=row["prompt_preview"],
            latency_ms=row["latency_ms"]
        )
    
    def get_records(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        agent: Optional[str] = None,
        task: Optional[str] = None,
        user: Optional[str] = None,
        limit: int = 1000
    ) -> List[UsageRecord]:
        """Query usage records with filters."""
        query = "SELECT * FROM usage_records WHERE 1=1"
        params: List[Any] = []
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())
        
        if agent:
            query += " AND agent = ?"
            params.append(agent)
        
        if task:
            query += " AND task = ?"
            params.append(task)
        
        if user:
            query += " AND user = ?"
            params.append(user)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            return [self._row_to_record(row) for row in cursor.fetchall()]
    
    def get_total_cost(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> float:
        """Get total cost in time range."""
        query = "SELECT COALESCE(SUM(total_cost), 0) as total FROM usage_records WHERE 1=1"
        params: List[Any] = []
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())
        
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            return float(row["total"]) if row else 0.0
    
    def get_costs_by_agent(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get cost breakdown by agent."""
        query = """
            SELECT 
                agent,
                SUM(total_cost) as total_cost,
                SUM(total_tokens) as total_tokens,
                COUNT(*) as request_count,
                AVG(total_cost) as avg_cost
            FROM usage_records 
            WHERE 1=1
        """
        params: List[Any] = []
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())
        
        query += " GROUP BY agent ORDER BY total_cost DESC"
        
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_costs_by_task(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get cost breakdown by task."""
        query = """
            SELECT 
                task,
                agent,
                SUM(total_cost) as total_cost,
                SUM(total_tokens) as total_tokens,
                COUNT(*) as request_count,
                AVG(total_cost) as avg_cost
            FROM usage_records 
            WHERE 1=1
        """
        params: List[Any] = []
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())
        
        query += " GROUP BY task, agent ORDER BY total_cost DESC"
        
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_expensive_prompts(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get most expensive prompts."""
        query = """
            SELECT 
                prompt_hash,
                prompt_preview,
                agent,
                task,
                model,
                AVG(total_tokens) as avg_tokens,
                AVG(total_cost) as avg_cost,
                COUNT(*) as call_count,
                SUM(total_cost) as total_cost
            FROM usage_records 
            WHERE prompt_hash IS NOT NULL
        """
        params: List[Any] = []
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())
        
        query += " GROUP BY prompt_hash ORDER BY avg_cost DESC LIMIT ?"
        params.append(limit)
        
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]


class InMemoryStorage(StorageBackend):
    """In-memory storage backend for testing."""
    
    def __init__(self):
        self.records: List[UsageRecord] = []
    
    def save(self, record: UsageRecord) -> None:
        self.records.append(record)
    
    def get_records(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        agent: Optional[str] = None,
        task: Optional[str] = None,
        user: Optional[str] = None,
        limit: int = 1000
    ) -> List[UsageRecord]:
        filtered = self.records
        
        if start_time:
            filtered = [r for r in filtered if r.timestamp >= start_time]
        if end_time:
            filtered = [r for r in filtered if r.timestamp <= end_time]
        if agent:
            filtered = [r for r in filtered if r.agent == agent]
        if task:
            filtered = [r for r in filtered if r.task == task]
        if user:
            filtered = [r for r in filtered if r.user == user]
        
        return sorted(filtered, key=lambda r: r.timestamp, reverse=True)[:limit]
    
    def get_total_cost(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> float:
        filtered = self.records
        
        if start_time:
            filtered = [r for r in filtered if r.timestamp >= start_time]
        if end_time:
            filtered = [r for r in filtered if r.timestamp <= end_time]
        
        return sum(r.total_cost for r in filtered)
