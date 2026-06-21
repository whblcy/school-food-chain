"""
应用配置 — 基于 pydantic-settings。
所有配置从环境变量（.env 文件）读取，缺省值仅用于开发环境。
"""
from __future__ import annotations

import os
from typing import List, Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_cors_origins(v):
    """支持逗号分隔的字符串或 JSON 数组格式。"""
    if isinstance(v, str):
        return [o.strip() for o in v.split(",") if o.strip()]
    return v


class Settings(BaseSettings):
    # 应用信息
    APP_NAME: str = "School Food Chain"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"  # development / staging / production
    DEBUG: bool = False

    # 数据库
    DATABASE_URL: str = "sqlite:///./school_food.db"

    # Redis — 缓存 / Celery broker / Token 黑名单
    REDIS_URL: str = "redis://localhost:6379/0"

    # 安全配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    # access_token 默认为 30 分钟（原来的 1 天过长）
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # refresh_token 默认为 7 天
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # JWT 签名算法 — 生产环境推荐 RS256（非对称）
    # HS256: 对称密钥（SECRET_KEY），适合单体应用
    # RS256: RSA 非对称密钥对，公钥可分发给微服务验证，私钥仅签发服务持有
    JWT_ALGORITHM: str = "HS256"
    # RS256 私钥（PEM 格式，生产环境通过环境变量或文件挂载注入）
    JWT_PRIVATE_KEY: str = ""
    # RS256 公钥（PEM 格式）
    JWT_PUBLIC_KEY: str = ""
    # 私钥/公钥文件路径（优先于内联字符串）
    JWT_PRIVATE_KEY_PATH: str = ""
    JWT_PUBLIC_KEY_PATH: str = ""

    # HttpOnly Cookie 配置 — 防 XSS 窃取 token
    # 启用后，登录/刷新接口会同时返回 Cookie 和 JSON body
    # 前端可选择使用 Cookie（更安全）或 Bearer Token（跨端兼容）
    COOKIE_ENABLED: bool = True
    COOKIE_SECURE: bool = False  # 生产环境必须为 True（仅 HTTPS 传输）
    COOKIE_SAMESITE: str = "lax"  # strict / lax / none
    COOKIE_DOMAIN: str = ""  # 留空则不设置 domain

    # CORS 允许来源（逗号分隔字符串或 JSON 数组）
    CORS_ORIGINS: List[str] = ["*"]

    # MinIO 文件存储
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "school-food"
    # 是否使用 HTTPS
    MINIO_SECURE: bool = False

    # 分页默认
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        return _parse_cors_origins(v)

    @model_validator(mode="after")
    def validate_production_security(self):
        """生产环境强制要求安全配置。"""
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY == "your-secret-key-change-in-production":
                raise ValueError("生产环境必须设置 SECRET_KEY 环境变量")
            if self.DEBUG:
                raise ValueError("生产环境不能开启 DEBUG")
            if "*" in self.CORS_ORIGINS:
                raise ValueError("生产环境不能使用 CORS_ORIGINS=*")
            # 生产环境强制 RS256 + HttpOnly Cookie
            if self.JWT_ALGORITHM != "RS256":
                raise ValueError("生产环境必须使用 RS256 算法（设置 JWT_ALGORITHM=RS256）")
            if not self.JWT_PRIVATE_KEY and not self.JWT_PRIVATE_KEY_PATH:
                raise ValueError("生产环境必须配置 JWT_PRIVATE_KEY 或 JWT_PRIVATE_KEY_PATH")
            if not self.JWT_PUBLIC_KEY and not self.JWT_PUBLIC_KEY_PATH:
                raise ValueError("生产环境必须配置 JWT_PUBLIC_KEY 或 JWT_PUBLIC_KEY_PATH")
            if not self.COOKIE_SECURE:
                raise ValueError("生产环境必须开启 COOKIE_SECURE（HTTPS）")
        return self

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
