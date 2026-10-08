from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass

class Monitor(Base):
    __tablename__="monitors"

    id:Mapped[int]=mapped_column(primary_key=True)
    name:Mapped[str]=mapped_column(String(255))
    url:Mapped[str]=mapped_column(String(2048))