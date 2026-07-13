from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from typing import AsyncIterator

class Conexion:
    def __init__(self, user:str, password:str, host:str, db:str) -> None:
        self.user = user
        self.password = password
        self.host = host
        self.db = db
        self.engine = create_async_engine(
            f'postgresql+asyncpg://{user}:{password}@{host}:6432/{db}',
            connect_args = {
                "statement_cache_size":0,
                "prepared_statement_cache_size":0
            })
        self.async_session_maker = sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    @asynccontextmanager

    async def get_session(self) -> AsyncIterator[AsyncSession]:

        async with self.async_session_maker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise