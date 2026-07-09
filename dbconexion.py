from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from contextlib import contextmanager
from typing import Iterator

class Conexion:
    def __init__(self,user:str, password:str, host:str, db:str):
        self.user = user
        self.password = password
        self.host = host
        self.db = db
        self.engine = create_engine(
            f'postgresql+psycopg2://{user}:{password}@{host}:5432/{db}')

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


    