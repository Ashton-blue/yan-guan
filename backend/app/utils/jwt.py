import jwt
from datetime import datetime, timedelta
from typing import Optional
from app.config import settings

def _encode(payload: dict, expire: datetime) -> str:
    """统一的签发入口。

    注意：PyJWT >= 2.10 按 RFC 7519 强校验 sub 必须是字符串，
    传 int 会在 decode 时抛 InvalidSubjectError（表现为登录拿到 token 但一律 401）。
    这里统一把 sub 规范成字符串。
    """
    to_encode = dict(payload)
    if "sub" in to_encode and to_encode["sub"] is not None:
        to_encode["sub"] = str(to_encode["sub"])
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    expire = datetime.utcnow() + (expires_delta or timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS))
    return _encode(data, expire)

def create_refresh_token(data: dict):
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return _encode(data, expire)

def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def get_subject(payload: Optional[dict]) -> Optional[int]:
    """从 payload 取用户 ID，兼容历史签发的 int / str 两种 sub。"""
    if not payload:
        return None
    raw = payload.get("sub")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None
