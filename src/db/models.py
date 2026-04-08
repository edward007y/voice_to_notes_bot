from sqlalchemy import BigInteger, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    # Telegram ID буде нашим унікальним ідентифікатором
    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    language_code: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Ключі можуть бути порожніми, поки юзер їх не додасть
    notion_api_key: Mapped[str | None] = mapped_column(String, nullable=True)
    notion_db_id: Mapped[str | None] = mapped_column(String, nullable=True)
