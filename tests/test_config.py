from app.config import get_settings


def test_default_configuration_is_available() -> None:
    settings = get_settings()

    assert settings.app_name == "Data Engineering Learning Coach"
    assert settings.database_url.startswith("sqlite")
