from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(70), nullable=False)
    cedula: Mapped[str] = mapped_column(String(12), nullable=False, unique=True)

    def __repr__(self) -> str:
        return f"User: (name: {self.name}, cedula: {self.cedula})"