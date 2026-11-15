import pytest

from app.core.config import normalize_database_url as n


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        (
            "postgresql://u:p@ep-x.aws.neon.tech/neondb?sslmode=require&channel_binding=require",
            "postgresql+asyncpg://u:p@ep-x.aws.neon.tech/neondb?ssl=require",
        ),
        ("postgres://u:p@h:5432/db", "postgresql+asyncpg://u:p@h:5432/db"),
        ("postgresql+asyncpg://u:p@h/db?ssl=require", "postgresql+asyncpg://u:p@h/db?ssl=require"),
        (" postgresql://u:p@h/db?channel_binding=require ", "postgresql+asyncpg://u:p@h/db"),
    ],
)
def test_normalize_database_url(given, expected):
    assert n(given) == expected


def test_frontend_origin_is_normalised():
    from app.core.config import Settings

    assert Settings(frontend_origin=" https://BeABeast.pages.dev/ ").frontend_origin == (
        "https://beabeast.pages.dev"
    )
