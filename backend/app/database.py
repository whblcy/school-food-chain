"""
数据库配置。
- 使用 SQLAlchemy 2.0 风格的 Engine + sessionmaker
- 根据 settings.DATABASE_URL 自动适配 PostgreSQL / SQLite
- 添加连接池配置，避免数据库连接耗尽
- 为 Alembic 提供 declarative Base
"""
from __future__ import annotations

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from app.config import settings

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

_engine_kwargs = dict(
    pool_pre_ping=True,            # 每次连接前检查是否仍然有效
    pool_recycle=1800,             # 30 分钟后回收连接，避免 PG 超时断开
    connect_args={},
)

if _is_sqlite:
    # SQLite 只能单线程写入，使用 StaticPool 保持单连接
    from sqlalchemy.pool import StaticPool
    _engine_kwargs.update(poolclass=StaticPool)
    _engine_kwargs["connect_args"].update(check_same_thread=False)
else:
    # PostgreSQL: 配置合理的连接池
    _engine_kwargs.update(
        pool_size=10,                # 长期保持 10 个连接
        max_overflow=20,              # 峰值最多再开 20 个
        pool_timeout=30,              # 30 秒拿不到连接则报错
    )


engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)

# SessionLocal = 生成独立 session 的工厂函数
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 风格的 declarative base（替代已废弃的 declarative_base()）。"""
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — 为每个请求提供一个数据库 session。

    用法:
        @app.get("/items")
        def list_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
