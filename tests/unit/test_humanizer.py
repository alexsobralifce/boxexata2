from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from src.application.services.humanizer import get_greeting, BRASILIA_TZ

def test_greeting_morning() -> None:
    # 05h00 to 11h59 -> Bom dia
    with patch("src.application.services.humanizer.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 6, 11, 8, 0, 0, tzinfo=timezone.utc).astimezone(BRASILIA_TZ)
        # 8 UTC is 5 Brasília time (8 - 3)
        assert "Bom dia" in get_greeting()

def test_greeting_afternoon() -> None:
    # 12h00 to 17h59 -> Boa tarde
    with patch("src.application.services.humanizer.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 6, 11, 15, 0, 0, tzinfo=timezone.utc).astimezone(BRASILIA_TZ)
        # 15 UTC is 12 Brasília time (15 - 3)
        assert "Boa tarde" in get_greeting()

def test_greeting_night() -> None:
    # 18h00 to 04h59 -> Boa noite
    with patch("src.application.services.humanizer.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 6, 11, 21, 0, 0, tzinfo=timezone.utc).astimezone(BRASILIA_TZ)
        # 21 UTC is 18 Brasília time (21 - 3)
        assert "Boa noite" in get_greeting()
