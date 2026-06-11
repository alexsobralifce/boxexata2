import pytest
from src.domain.value_objects.phone_number import PhoneNumber


def test_phone_number_success() -> None:
    phone = PhoneNumber("55 (88) 99999-0000")
    assert phone.normalized == "5588999990000"
    assert phone.whatsapp_jid() == "5588999990000@s.whatsapp.net"


def test_phone_number_too_short_raises_error() -> None:
    with pytest.raises(ValueError, match="Número de telefone inválido"):
        PhoneNumber("12345678")
