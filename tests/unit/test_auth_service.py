from datetime import timedelta
import jwt
from src.application.services.auth_service import (
    verify_password,
    get_password_hash,
    create_access_token,
    verify_token,
)


def test_password_hashing() -> None:
    # Arrange
    plain_password = "minha_senha_super_secreta"

    # Act
    hashed = get_password_hash(plain_password)

    # Assert
    assert hashed != plain_password
    assert hashed.startswith("$2b$")  # Indica hash bcrypt
    assert verify_password(plain_password, hashed) is True
    assert verify_password("senha_errada", hashed) is False


def test_verify_password_with_empty_or_invalid_hash() -> None:
    assert verify_password("senha", "") is False
    assert verify_password("senha", "hash_invalido") is False


def test_jwt_token_generation_and_validation() -> None:
    # Arrange
    user_data = {"sub": "admin_test"}

    # Act
    token = create_access_token(user_data)
    username = verify_token(token)

    # Assert
    assert token is not None
    assert isinstance(token, str)
    assert username == "admin_test"


def test_jwt_token_validation_expired() -> None:
    # Arrange
    user_data = {"sub": "admin_test"}
    # Token expirado com timedelta negativo
    token = create_access_token(user_data, expires_delta=timedelta(minutes=-10))

    # Act
    username = verify_token(token)

    # Assert
    assert username is None


def test_jwt_token_validation_invalid_signature() -> None:
    # Arrange
    # Token assinado com outra chave
    invalid_token = jwt.encode({"sub": "admin_test"}, "outra_chave_qualquer", algorithm="HS256")

    # Act
    username = verify_token(invalid_token)

    # Assert
    assert username is None
