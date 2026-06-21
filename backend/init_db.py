"""
一次性初始化脚本：
  1) 建表（SQLAlchemy 自动建，不依赖 Alembic）
  2) 创建默认组织 + 两个用户 + 示例食材

用法:
  cd backend
  python init_db.py

注意：已存在同名用户时，会重置其密码（以保证与当前 bcrypt 实现对齐）。
"""
from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base
from app.auth import get_password_hash
from app.models import (
    Organization, OrgType, User, UserRole,
    Category, Ingredient, Supplier,
)


def _echo(msg):
    print(msg)


def main():
    _echo(f"[1] DATABASE_URL = {settings.DATABASE_URL}")

    connect_args = {}
    if "sqlite" in settings.DATABASE_URL:
        connect_args["check_same_thread"] = False
    engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)

    _echo("[2] 建表 ...")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # --- 组织 ---
        org = db.query(Organization).filter(Organization.name == "示范中小学").first()
        if not org:
            org = Organization(
                name="示范中小学",
                code="DEMO-001",
                org_type=OrgType.CAMPUS,
                address="XX市XX区XX路1号",
                contact_person="张主任",
                contact_phone="13800000000",
                is_active=True,
            )
            db.add(org)
            db.flush()
            _echo(f"    ✓ 组织: id={org.id} name={org.name}")
        else:
            _echo(f"    → 组织已存在: id={org.id}")
        org_id = org.id

        # --- 分类 ---
        for code, name in [("GRAIN", "米面"), ("VEG", "蔬菜"), ("MEAT", "肉类"), ("SEASON", "调味品")]:
            if not db.query(Category).filter(Category.name == name).first():
                db.add(Category(code=code, name=name, is_active=True, org_id=org_id))
                _echo(f"    ✓ 分类: {name}")
        db.flush()

        # --- 供应商 ---
        sup = db.query(Supplier).filter(Supplier.name == "示例食品有限公司").first()
        if not sup:
            sup = Supplier(
                name="示例食品有限公司",
                code="SUP-001",
                contact_person="李经理",
                phone="13900000000",
                email="contact@example.com",
                address="XX市XX区食品工业区",
                org_id=org_id,
            )
            db.add(sup)
            db.flush()
            _echo(f"    ✓ 供应商: id={sup.id}")

        # --- 用户 admin ---
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                email="admin@example.com",
                real_name="系统管理员",
                hashed_password=get_password_hash("admin123"),
                role=UserRole.SUPER_ADMIN,
                org_id=org_id,
                is_active=True,
            )
            db.add(admin)
            _echo(f"    ✓ SUPER_ADMIN: admin / admin123")
        else:
            admin.hashed_password = get_password_hash("admin123")
            admin.org_id = org_id
            admin.role = UserRole.SUPER_ADMIN
            _echo(f"    → admin 已存在，重置密码为 admin123 (bcrypt 新哈希)")

        # --- 用户 school_user ---
        school_user = db.query(User).filter(User.username == "school_user").first()
        if not school_user:
            school_user = User(
                username="school_user",
                email="school@example.com",
                real_name="学校用户",
                hashed_password=get_password_hash("school123"),
                role=UserRole.OPERATOR,
                org_id=org_id,
                is_active=True,
            )
            db.add(school_user)
            _echo(f"    ✓ 普通用户: school_user / school123")

        # --- 示例食材 ---
        rice_cat = db.query(Category).filter(Category.name == "米面").first()
        if db.query(Ingredient).count() == 0 and rice_cat and sup:
            for name, code, unit, safety in [
                ("大米", "RICE-001", "kg", 50),
                ("面粉", "FLOUR-001", "kg", 30),
                ("食用油", "OIL-001", "L", 20),
            ]:
                db.add(Ingredient(
                    name=name, code=code, unit=unit, safety_stock=safety,
                    current_stock=100, category_id=rice_cat.id,
                    supplier_id=sup.id, org_id=org_id, is_active=True,
                ))
            _echo("    ✓ 写入 3 条示例食材")

        db.commit()
        _echo("\n[✓] 初始化完成。")
        _echo("    - admin / admin123  (SUPER_ADMIN)")
        _echo("    - school_user / school123  (普通用户)")

    except Exception as exc:
        db.rollback()
        print(f"[X] 初始化失败: {exc}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
