from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from contextlib import contextmanager
from typing import Iterator
from sqlalchemy.pool import NullPool
class Conexion:
    def __init__(self,user:str, password:str, host:str, db:str):
        self.user = user
        self.password = password
        self.host = host
        self.db = db
        self.engine = create_engine(
            f'postgresql+psycopg2://{user}:{password}@{host}:6432/{db}', poolclass=NullPool)
        #desactivamos el pool de sqlalchemy para que trabaje directamente con pgbouncer

    @contextmanager  
    def get_session(self) -> Iterator[Session]:
        
        session = Session(self.engine)

        try:
            yield session

            #session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


    