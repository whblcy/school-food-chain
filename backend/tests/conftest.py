"""
pytest 配置文件 - 提供测试用的数据库 session、FastAPI TestClient 和认证 token fixtures。

使用 SQLite 内存数据库替代 PostgreSQL，避免测试依赖真实数据库。
通过 dependency_overrides 注入测试数据库 session 到 FastAPI 应用中。
"""
import os
from datetime import datetime

# ---------------------------------------------------------------------------
# 在导入 app 模块之前，将 DATABASE_URL 环境变量覆盖为 SQLite 内存数据库。
# pydantic-settings 会优先读取环境变量，从而避免尝试连接 PostgreSQL。
# ---------------------------------------------------------------------------
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User, UserRole, Organization, OrgType, Category, Supplier, SupplierStatus, Ingredient
from app.auth import get_password_hash, create_access_token, create_refresh_token

# ---------------------------------------------------------------------------
# 测试用 SQLite 内存数据库引擎
# 使用 StaticPool 确保所有 session 共享同一个内存数据库连接
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------------
# SQLite 不支持 server_default=func.now()，通过 SQLAlchemy 事件在插入前
# 自动为 created_at 和 updated_at 字段填充当前时间。
# ---------------------------------------------------------------------------
@event.listens_for(engine, "before_execute")
def _sqlite_datetime_defaults(conn, clauseelement, multiparams, params, execution_options=None):
    """在执行 SQL 前为 SQLite 自动填充 datetime 默认值。"""
    for param_set in params:
        if isinstance(param_set, dict):
            for key, value in list(param_set.items()):
                if value is None and key in ("created_at", "updated_at"):
                    param_set[key] = datetime.utcnow()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """在测试会话开始时创建所有表，结束时清理。"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """
    提供一个独立的数据库 session，每个测试结束后自动回滚。

    使用 yield + rollback 模式确保测试之间数据隔离，
    避免前一个测试的数据影响后一个测试。
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    """
    提供配置了测试数据库的 FastAPI TestClient。

    通过 dependency_overrides 将应用中的 get_db 替换为
    返回测试数据库 session 的函数，从而实现数据库隔离。
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # 由 db_session fixture 负责清理

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_org(db_session):
    """
    创建一个测试用的组织（学校食堂）。

    Returns:
        Organization: 测试组织实例
    """
    org = Organization(
        name="测试学校食堂",
        code="TEST-SCHOOL-001",
        org_type=OrgType.CANTEEN,
        address="测试市测试区测试路1号",
        contact_person="张管理",
        contact_phone="13800138000",
        is_active=True,
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


@pytest.fixture
def test_category(db_session, test_org):
    """
    创建一个测试用的食材分类。

    Returns:
        Category: 测试分类实例
    """
    category = Category(
        name="蔬菜类",
        code="VEG",
        description="各类新鲜蔬菜",
        sort_order=1,
        is_active=True,
        org_id=test_org.id,
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


@pytest.fixture
def test_supplier(db_session, test_org):
    """
    创建一个测试用的供应商。

    Returns:
        Supplier: 测试供应商实例
    """
    supplier = Supplier(
        name="测试食材供应商",
        code="SUP-TEST-001",
        contact_person="李经理",
        phone="13900139000",
        email="test@example.com",
        address="测试市供应商路100号",
        status=SupplierStatus.ACTIVE,
        rating=4.5,
        org_id=test_org.id,
    )
    db_session.add(supplier)
    db_session.commit()
    db_session.refresh(supplier)
    return supplier


@pytest.fixture
def test_user(db_session, test_org):
    """
    创建一个测试用的管理员用户。

    Returns:
        User: 测试用户实例
    """
    user = User(
        username="admin",
        email="admin@test.com",
        phone="13700137000",
        hashed_password=get_password_hash("admin123"),
        real_name="管理员",
        role=UserRole.ADMIN,
        org_id=test_org.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_operator(db_session, test_org):
    """
    创建一个测试用的操作员用户。

    Returns:
        User: 测试操作员实例
    """
    user = User(
        username="operator",
        email="operator@test.com",
        phone="13700137001",
        hashed_password=get_password_hash("operator123"),
        real_name="操作员",
        role=UserRole.OPERATOR,
        org_id=test_org.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_token(test_user):
    """
    生成管理员用户的 access token。

    Returns:
        str: JWT access token 字符串
    """
    return create_access_token(data={"sub": str(test_user.id)})


@pytest.fixture
def operator_token(test_operator):
    """
    生成操作员用户的 access token。

    Returns:
        str: JWT access token 字符串
    """
    return create_access_token(data={"sub": str(test_operator.id)})


@pytest.fixture
def admin_refresh_token(test_user):
    """
    生成管理员用户的 refresh token。

    Returns:
        str: JWT refresh token 字符串
    """
    return create_refresh_token(data={"sub": str(test_user.id)})


@pytest.fixture
def admin_auth_headers(admin_token):
    """
    生成管理员用户的认证请求头。

    Returns:
        dict: 包含 Authorization Bearer token 的请求头字典
    """
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def operator_auth_headers(operator_token):
    """
    生成操作员用户的认证请求头。

    Returns:
        dict: 包含 Authorization Bearer token 的请求头字典
    """
    return {"Authorization": f"Bearer {operator_token}"}


@pytest.fixture
def test_ingredient(db_session, test_category, test_supplier, test_org):
    """
    创建一个测试用的食材记录。

    Returns:
        Ingredient: 测试食材实例
    """
    ingredient = Ingredient(
        name="大白菜",
        code="ING-001",
        category_id=test_category.id,
        unit="千克",
        specification="新鲜无腐烂",
        safety_stock=50.0,
        current_stock=100.0,
        supplier_id=test_supplier.id,
        org_id=test_org.id,
        is_active=True,
    )
    db_session.add(ingredient)
    db_session.commit()
    db_session.refresh(ingredient)
    return ingredient
