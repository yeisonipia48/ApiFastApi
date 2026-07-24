
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from functools import lru_cache
from sqlalchemy import select
from alembicApi import models
from schemas import UserCreate, UserUpdate
from dbconexion import Conexion
from typing import AsyncGenerator, List


@lru_cache
def _get_con() -> Conexion:
    with open('/run/secrets/postgres_user') as f:
        db_user = f.read().strip()

    with open('/run/secrets/postgres_password') as f:
        password = f.read().strip()

    with open('/run/secrets/postgres_host') as f:
        host = f.read().strip()

    with open('/run/secrets/postgres_db') as f:
        db = f.read().strip()
    return Conexion(db_user,password,host,db)

def get_con() -> Conexion:
    return _get_con()

async def get_conexion() -> AsyncGenerator[AsyncSession, None]:
    async with get_con().get_session() as session:
        yield session

class UserRepository:

    def __init__(self, session: AsyncSession = Depends(get_conexion)):
        self.session = session
    
    async def get_all(self) -> List[models.User]:
        query = select(models.User)
        users = await self.session.scalars(query)
        return users.all()
    
    async def get_by_id(self, id:int) -> models.User | None:
        user = await self.session.get(models.User, id)
        return user
    
    async def get_by_cedula(self, cedula:str) -> models.User | None:
        query = select(models.User).where(models.User.cedula == cedula)
        user = await self.session.scalars(query.limit(1))
        return user.first()
    
    async def create(self, usuario: UserCreate) -> models.User:
        user = models.User(
            name = usuario.name,
            cedula = usuario.cedula
        )

        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def update(self, id:int, usuario: UserUpdate) -> models.User | None:
        user_update = await self.get_by_id(id)
        if not user_update:
            return None
        data_update = usuario.model_dump(exclude_unset=True)
        for key, value in data_update.items():
            setattr(user_update, key, value)
        await self.session.commit()
        await self.session.refresh(user_update)
        return user_update
        
    async def delete(self, id:int) -> bool:
        user_delete = await self.get_by_id(id)
        if not user_delete:
            return False
        
        await self.session.delete(user_delete)
        await self.session.commit()
        return True
        
