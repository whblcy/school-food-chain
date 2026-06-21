"""
认证路由
- POST /auth/login — JWT 登录（同时设置 HttpOnly Cookie）
- POST /auth/refresh — 使用 refresh_token 换发新的 token
- POST /auth/logout — 把 access_token 加入黑名单 + 清除 Cookie
- GET /auth/me — 返回当前用户信息（前端 auth store 调用）
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit_utils import write_audit_log
from app.auth import (
    verify_password, create_access_token, create_refresh_token,
    decode_token, rate_limiter, blacklist, get_current_user,
    set_auth_cookies, clear_auth_cookies,
)
from app.config import settings
from app.database import get_db
from app.models import User

router = APIRouter()
security = HTTPBearer()


# ---------------------------------------------------------------------------
# 请求/响应模型
# ---------------------------------------------------------------------------
class UserLogin(BaseModel):
    username: str
    password: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


class UserInfo(BaseModel):
    id: int
    username: str
    email: str | None
    real_name: str | None
    role: str
    org_id: int | None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------
@router.post("/login", response_model=Token)
def login(credentials: UserLogin, request: Request, response: Response, db: Session = Depends(get_db)):
    # 1) 基于用户名的限流
    if rate_limiter.is_blocked(credentials.username):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please try again later.",
        )

    # 2) 查询用户（is_active 检查合并到此处，避免被用于枚举有效用户名）
    user = db.query(User).filter(User.username == credentials.username).first()
    if (not user
            or not verify_password(credentials.password, user.hashed_password)
            or not user.is_active):
        rate_limiter.record_failure(credentials.username)
        write_audit_log(
            db, request, user, action="login_failed",
            target_type="user", target_id=user.id if user else None,
            new_value={"username": credentials.username},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # 3) 记录最后登录时间
    user.last_login = datetime.now(timezone.utc)
    write_audit_log(
        db, request, user, action="login",
        target_type="user", target_id=user.id,
    )
    db.commit()

    # 4) 登录成功，清除失败计数
    rate_limiter.reset(credentials.username)

    # 5) 生成 token
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    # 6) 设置 HttpOnly Cookie（防 XSS）
    set_auth_cookies(response, access_token, refresh_token)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.post("/refresh", response_model=Token)
def refresh_token(credentials: HTTPAuthorizationCredentials = Depends(security),
                  response: Response = None,
                  db: Session = Depends(get_db)):
    refresh_token_str = credentials.credentials
    # 黑名单检查
    if blacklist.is_blacklisted(refresh_token_str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    payload = decode_token(refresh_token_str)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # 令牌轮换：将旧 refresh_token 加入黑名单，使其立即失效
    blacklist.add(refresh_token_str)

    new_access = create_access_token(data={"sub": str(user.id)})
    new_refresh = create_refresh_token(data={"sub": str(user.id)})

    # 轮换 Cookie
    if response is not None:
        set_auth_cookies(response, new_access, new_refresh)

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    body: LogoutRequest | None = Body(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """把当前 access_token（及可选的 refresh_token）加入黑名单，阻止其继续使用。"""
    blacklist.add(credentials.credentials)
    if body and body.refresh_token:
        blacklist.add(body.refresh_token)
    # 清除 HttpOnly Cookie
    clear_auth_cookies(response)
    write_audit_log(
        db, request, current_user, action="logout",
        target_type="user", target_id=current_user.id,
    )
    db.commit()
    return {"message": "Logged out"}


@router.get("/me", response_model=UserInfo)
def get_me(current_user: User = Depends(get_current_user)):
    """返回当前登录用户信息（前端 auth store 登录后会调用）。"""
    return UserInfo(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        real_name=current_user.real_name,
        role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        org_id=current_user.org_id,
    )
