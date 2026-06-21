"""
Alembic 迁移环境配置。
- 自动从 SQLAlchemy Base metadata 生成迁移
- 从 settings.DATABASE_URL 读取数据库连接
"""
from logging.config import fileConfig
import os
import sys

from sqlalchemy import engine_from_config, pool
from alembic import context

# 把 backend 目录加入 Python path，使其可以 import app.*
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _BACKEND_ROOT)

from app.database import Base
from app.config import settings
import app.models  # noqa: F401 — 注册所有模型到 Base.metadata，autogenerate 才能检测变更

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# SQLAlchemy model metadata — 用于 autogenerate
target_metadata = Base.metadata

# 用 settings.DATABASE_URL 覆盖 alembic.ini 中的 sqlalchemy.url
# 这样无需在两处维护数据库地址
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)


def run_migrations_offline() -> None:
    """以 offline 模式运行迁移。
    直接向数据库发送 SQL 字符串，不通过 DBAPI。
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """以 online 模式运行迁移（通过 DBAPI 连接数据库）。"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,           # 比较列类型变化
            compare_server_default=True,  # 比较默认值变化
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
