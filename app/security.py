from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, Header, HTTPException
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import User

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(user: User) -> str:
    payload = {
        'sub': str(user.id),
        'role': user.role,
        'type': 'access',
        'exp': datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user: User) -> str:
    payload = {
        'sub': str(user.id),
        'role': user.role,
        'type': 'refresh',
        'exp': datetime.utcnow() + timedelta(minutes=settings.JWT_REFRESH_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str):
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


def _extract_bearer(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail='Authentication required')
    raw = authorization
    if raw.lower().startswith('bearer '):
        raw = raw[7:]
    return raw.strip()


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    token = _extract_bearer(authorization)
    try:
        payload = decode_token(token)
        if payload.get('type') not in {'access', None}:
            raise HTTPException(status_code=401, detail='Invalid token type')
        user_id = int(payload['sub'])
    except (JWTError, ValueError, KeyError):
        raise HTTPException(status_code=401, detail='Invalid token')
    user = db.get(User, user_id)
    if not user or not user.active:
        raise HTTPException(status_code=401, detail='Invalid user')
    return user


def require_roles(*roles: str):
    def dep(user: User = Depends(get_current_user)):
        if roles and user.role not in roles:
            raise HTTPException(status_code=403, detail='Forbidden')
        return user

    return dep
