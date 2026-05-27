from sqlalchemy import create_engine
from sqlalchemy.engine import Connection
from contextlib import contextmanager
from typing import Iterator

class Conexion:
    def __init__(self,user:str, password:str, host:str):
        self.user = user
        self.password = password
        self.host = host
        self.engine = create_engine(
            f'postgresql+psycopg2://{user}:{password}@{host}:5432/api')

    @contextmanager  
    def conexion(self) -> Iterator[Connection]:
        with self.engine.begin() as con:
            yield con


    