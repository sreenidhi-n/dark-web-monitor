import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# auto_error=False so we can check both schemes in get_current_user before rejecting
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class Token(BaseModel):
    access_token: str
    token_type: str


class UserOut(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


class ApiKeyOut(BaseModel):
    api_key: str


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": subject, "exp": expire}, settings.secret_key, algorithm=settings.jwt_algorithm)


async def _user_by_email(email: str, db: AsyncSession) -> User | None:
    result = await db.execute(select(User).where(User.email == email, User.is_active.is_(True)))
    return result.scalar_one_or_none()


async def _user_by_api_key(api_key: str, db: AsyncSession) -> User | None:
    result = await db.execute(select(User).where(User.api_key == api_key, User.is_active.is_(True)))
    return result.scalar_one_or_none()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    api_key: str = Depends(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> User:
    # Try Bearer JWT first
    if token:
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
            email: str | None = payload.get("sub")
            if email:
                user = await _user_by_email(email, db)
                if user:
                    return user
        except JWTError:
            pass

    # Fall back to API key header
    if api_key:
        user = await _user_by_api_key(api_key, db)
        if user:
            return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_role(*roles: str):
    """Dependency factory — raises 403 if the current user's role is not in `roles`."""
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user
    return _check


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/login", response_model=Token)
async def login(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await _user_by_email(form.username, db)
    if not user or not pwd_context.verify(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(user.email), token_type="bearer")


@router.post("/logout")
async def logout():
    # JWT is stateless — the client discards the token.
    # Add a Redis blocklist here if you need server-side revocation.
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/api-key", response_model=ApiKeyOut)
async def rotate_api_key(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Generate (or rotate) the API key for the authenticated user."""
    current_user.api_key = secrets.token_hex(32)
    db.add(current_user)
    await db.commit()
    return ApiKeyOut(api_key=current_user.api_key)
