from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from src.application.services.auth_service import verify_token
from src.shared.config import settings

# Rota onde o token de login pode ser gerado/obtido
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/admin/login")


async def get_current_admin(token: str = Depends(oauth2_scheme)) -> str:
    """Dependência FastAPI que garante que a requisição está autenticada com um token JWT válido

    de administrador.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais de login inválidas ou token expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    username = verify_token(token)
    if username is None:
        raise credentials_exception

    # Verifica se corresponde ao administrador configurado
    if username != settings.admin_username:
        raise credentials_exception

    return username
