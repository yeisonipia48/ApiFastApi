from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from schemas import Usuarios, UserUpdate, UserCreate
from typing import List
from repository import UserRepository, get_con
from alembicApi import models
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await get_con().engine.dispose()

app = FastAPI(lifespan=lifespan)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Error interno del servidor"},
    )

@app.get('/')
async def saludo() -> str:
    return "Hola Ing Yeison Ipia, mucho gusto"

@app.get('/users', response_model=List[Usuarios])
async def users(repo: UserRepository = Depends()) -> List[models.User]:
    return await repo.get_all()
    
@app.get('/users/{id}', response_model=Usuarios)
async def get_user_by_id(id:int, repo: UserRepository = Depends()) -> models.User:
    user = await repo.get_by_id(id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Usuario no encontrado.")
    return user
    
@app.post('/users', status_code=status.HTTP_201_CREATED, response_model=Usuarios)
async def user_create(usuario: UserCreate, repo: UserRepository = Depends()) -> models.User:
    cedula = await repo.get_by_cedula(usuario.cedula)
    if cedula:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="La cedula ya esta registrada en la base de datos.")
    return await repo.create(usuario)

    
@app.patch('/users/{id}', response_model=Usuarios)
async def user_partial_update(id:int, usuario: UserUpdate, repo: UserRepository = Depends()) -> models.User:
    user_update = await repo.update(id, usuario)
    if not user_update:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Usuario no encontrado.")
    return user_update
    
@app.delete('/users/{id}')
async def user_delete(id:int, repo: UserRepository = Depends()) -> None:

    user_delete = await repo.delete(id)
    if not user_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Usuario no encontrado.")
    return None