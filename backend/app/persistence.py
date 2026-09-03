from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection

from app.checkpointing import create_checkpoint_serializer
from app.domain.models import ConfirmedMemory, MemoryCandidate, MemoryCategory


class MemoryRepository(Protocol):
    async def add(self, child_id: str, candidate: MemoryCandidate) -> ConfirmedMemory: ...

    async def list_for_child(self, child_id: str) -> list[ConfirmedMemory]: ...

    async def delete(self, child_id: str, memory_id: str) -> bool: ...


class InMemoryRepository:
    def __init__(self) -> None:
        self._items: dict[str, ConfirmedMemory] = {}

    async def add(self, child_id: str, candidate: MemoryCandidate) -> ConfirmedMemory:
        item = ConfirmedMemory(
            memory_id=str(uuid4()),
            child_id=child_id,
            summary=candidate.summary,
            category=candidate.category,
            created_at=datetime.now(UTC),
        )
        self._items[item.memory_id] = item
        return item

    async def list_for_child(self, child_id: str) -> list[ConfirmedMemory]:
        return [item for item in reversed(self._items.values()) if item.child_id == child_id]

    async def delete(self, child_id: str, memory_id: str) -> bool:
        item = self._items.get(memory_id)
        if item is None or item.child_id != child_id:
            return False
        del self._items[memory_id]
        return True


class PostgresMemoryRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    async def setup(self) -> None:
        async with await AsyncConnection.connect(self._database_url) as connection:
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS child_memories (
                    memory_id UUID PRIMARY KEY,
                    child_id VARCHAR(64) NOT NULL,
                    summary VARCHAR(200) NOT NULL,
                    category VARCHAR(32) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL
                )
                """
            )
            await connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_child_memories_child_id ON child_memories(child_id)"
            )

    async def add(self, child_id: str, candidate: MemoryCandidate) -> ConfirmedMemory:
        item = ConfirmedMemory(
            memory_id=str(uuid4()),
            child_id=child_id,
            summary=candidate.summary,
            category=candidate.category,
            created_at=datetime.now(UTC),
        )
        async with await AsyncConnection.connect(self._database_url) as connection:
            await connection.execute(
                """
                INSERT INTO child_memories (memory_id, child_id, summary, category, created_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (item.memory_id, item.child_id, item.summary, item.category.value, item.created_at),
            )
        return item

    async def list_for_child(self, child_id: str) -> list[ConfirmedMemory]:
        async with await AsyncConnection.connect(self._database_url) as connection:
            cursor = await connection.execute(
                """
                SELECT memory_id, child_id, summary, category, created_at
                FROM child_memories
                WHERE child_id = %s
                ORDER BY created_at DESC
                """,
                (child_id,),
            )
            rows = await cursor.fetchall()
        return [
            ConfirmedMemory(
                memory_id=str(row[0]),
                child_id=row[1],
                summary=row[2],
                category=MemoryCategory(row[3]),
                created_at=row[4],
            )
            for row in rows
        ]

    async def delete(self, child_id: str, memory_id: str) -> bool:
        async with await AsyncConnection.connect(self._database_url) as connection:
            cursor = await connection.execute(
                "DELETE FROM child_memories WHERE child_id = %s AND memory_id = %s",
                (child_id, memory_id),
            )
            return cursor.rowcount > 0


@dataclass
class Persistence:
    checkpointer: object
    memory_repository: MemoryRepository


@asynccontextmanager
async def open_persistence(database_url: str | None) -> AsyncIterator[Persistence]:
    if not database_url:
        yield Persistence(
            InMemorySaver(serde=create_checkpoint_serializer()),
            InMemoryRepository(),
        )
        return

    repository = PostgresMemoryRepository(database_url)
    await repository.setup()
    async with AsyncPostgresSaver.from_conn_string(
        database_url, serde=create_checkpoint_serializer()
    ) as checkpointer:
        await checkpointer.setup()
        yield Persistence(checkpointer, repository)
