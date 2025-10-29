import asyncio
import datetime as dt

from dotenv import load_dotenv

from app.config import load_settings
from app.db.base import init_engine, session_factory
from app.db.models import Event


async def seed() -> None:
    load_dotenv()
    settings = load_settings()
    init_engine(settings.database_url)

    async with session_factory() as session:
        existing = await session.execute(Event.__table__.select().limit(1))
        if existing.first():
            print("Database already seeded")
            return
        events = [
            Event(
                title="Онлайн-вечер настольных игр",
                teaser="Соберёмся в уютном Zoom, чтобы поиграть всей семьёй",
                description="Расскажем про лучшие игры для тёплых вечеров и сыграем вместе. Формат: онлайн в Zoom.",
                date=dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=10),
                image_id="AgACAgIAAxkBAAICb2YyvX-cMAQw4ZcDeK11gQJwzH7AAAJ0rjEb2CTRSWffQqNVg_x8AQADAgADeAADNAQ",
                limit=200,
            ),
            Event(
                title="Мастер-класс по семейной кулинарии",
                teaser="Готовим праздничный десерт онлайн",
                description="Шеф-повар поделится рецептом и проведёт шаг за шагом. Формат: онлайн, все ингредиенты заранее.",
                date=dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=20),
                image_id="AgACAgIAAxkBAAICcWYyvh-9YgABVZh9-BANr_6IQ3QaAAJEqzEb2CTRSeFX7AJRnb8cAQADAgADeAADNAQ",
                limit=200,
            ),
        ]
        session.add_all(events)
        await session.commit()
        print("Seed data inserted")


if __name__ == "__main__":
    asyncio.run(seed())
