from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Any
from sqlalchemy import text, select, insert
from dbconexion import Conexion
from alembicApi import models

with open('/run/secrets/postgres_user') as f:
    db_user = f.read().strip()

with open('/run/secrets/postgres_password') as f:
    password = f.read().strip()

with open('/run/secrets/postgres_host') as f:
    host = f.read().strip()

with open('/run/secrets/postgres_db') as f:
    db = f.read().strip()

class Usuarios(BaseModel):
    id: int
    name: str
    cedula: str

class UserCreate(BaseModel):
    name: str
    cedula: str

class UserUpdate(BaseModel):
    name:str | None = None
    cedula:str | None = None

db = Conexion(db_user,password,host,db)
app = FastAPI()
@app.get('/')
def saludo() -> str:
    return "Hola Ing Yeison Ipia, mucho gusto"

@app.get('/user', response_model=List[Usuarios] )
def user()-> List[dict[str, Any]]:
    
    """with db.conexion() as con:
        query = text('select id, name, cedula from users;')
        r = con.execute(query).mappings().fetchall()
        usuarios = [dict(row) for row in r]
        return usuarios"""
    with db.get_session() as session:
        query = select(models.User)
        users = session.scalars(query).all()
        return users
    
@app.get('/user/search', response_model=Usuarios)
def search_user(id: int | None = None, cedula: str | None = None) -> dict[str, Any]:

    if id is None and cedula is None:
        raise HTTPException(status_code=400, detail="Debe proporcionar 'id' o 'cedula' para realizar la búsqueda")
    
    #with db.conexion() as con:
    #    query = text("""select id, name, cedula 
    #                    from users 
    #                    where 
    #                    (:id is null or id = :id)
    #                    and
    #                    (:cedula is null or cedula = :cedula)
    #                    limit 1;
    #                """)
    #    result = con.execute(query, {"id":id, "cedula" : cedula}).mappings().one_or_none()
    #    
    #    # Si el usuario no existe en la DB, respondemos con un elegante 404
    #    if not result:
    #        raise HTTPException(status_code=404, detail="Usuario no encontrado")
            
    #    return dict(result)
    
    with db.get_session() as session:

        query = select(models.User)

        if id is not None and cedula is not None:
            query = query.where(models.User.id == id and models.User.cedula == cedula)

        if id is not None:
            query = query.where(models.User.id == id)

        if cedula is not None:
            query = query.where(models.User.cedula == cedula)
        
        query = query.limit(1)

        user = session.scalars(query).first()

        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        return user


@app.post('/user', status_code=201)

def user_create(usuario: UserCreate) -> dict[str,str]:
    """with db.conexion() as con:

        query = text('insert into users(name, cedula) values(:name, :cedula)')
        con.execute(query, {"name":usuario.name, "cedula": usuario.cedula})
       
        return {"message": "Usuario Creado"}"""
    with db.get_session() as session:
        user = models.User(
            name = usuario.name,
            cedula = usuario.cedula
        )

        session.add(user)
        session.commit()
        return {"message": "Usuario Creado"}

    
@app.patch('/user/{id}')

def user_partial_update(id:int, usuario: UserUpdate) -> dict[str,str]:
    #with db.conexion() as con:

    #    query = text("""update users 
    #                 set name = COALESCE(:name, name), cedula = COALESCE(:cedula, cedula)
    #                 where id = :id""")
    #    result = con.execute(query, {"name":usuario.name, "cedula": usuario.cedula, "id":id})

    #    if result.rowcount == 0:
    #        raise HTTPException(status_code=404, detail="Usuario no encontrado")
             
    #    return {"message": "Usuario actualizado exitosamente"}

    with db.get_session() as session:

        user_update = session.get(models.User,id)

        if not user_update:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        if usuario.name is not None:
            user_update.name = usuario.name
            session.commit()

        if usuario.cedula is not None:
            user_update.cedula = usuario.cedula
            session.commit()

        return {"message":"Usuario actualizado"}


@app.delete('/user/{id}')
def user_delete(id:int)-> dict[str,str]:
    """with db.conexion() as con:
        query = text('delete from users where id = :id')
        result = con.execute(query, {"id":id})

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Usuario a eliminar no encontrado")
        
        return {"message": "Usuario eliminado exitosamente"}"""
    
    with db.get_session() as session:

        user_delete = session.get(models.User, id)

        if not user_delete:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        
        session.delete(user_delete)
        session.commit()
        
        return {"mesage":"usuario eliminado."}