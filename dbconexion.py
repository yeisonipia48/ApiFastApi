from sqlalchemy import create_engine
from contextlib import contextmanager

class Conexion:
    def __init__(self,user:str, password:str, host:str):
        self.user = user
        self.password = password
        self.host = host
        self.engine = create_engine(
            f'postgresql+psycopg2://{user}:{password}@{host}:5432/api')

    @contextmanager  
    def conexion(self):
        with self.engine.begin() as con:
            yield con


    