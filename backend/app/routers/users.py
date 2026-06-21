"""用户管理路由 — 多租户 org_id 隔离 + 角色权限。

权限策略：
- SUPER_ADMIN: 可管理所有组织的所有用户
- ADMIN: 可在本组织内创建/修改/删除用户；不能越权创建其它组织的用户
- 普通角色: 仅能查看用户列表，不能创建/修改/删除用户
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy.sql import false as sql_false
from typing import List

from app.database import get_db
from app.auth import get_current_user, get_password_hash
from app.models import User as UserModel, UserRole
from app.schemas import UserCreate, UserUpdate, User
from app.audit_utils import write_audit_log

router = APIRouter()


def _require_admin(current_user: UserModel) -> None:
    if current_user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )


def _filter_by_org(query, current_user: UserModel):
    """按当前用户的组织过滤。SUPER_ADMIN 能看所有组织。"""
    if current_user.role == UserRole.SUPER_ADMIN:
        return query
    if current_user.org_id is None:
        # 非超级管理员且无组织归属，返回空查询避免泄露孤儿用户
        return query.filter(sql_false())
    return query.filter(UserModel.org_id == current_user.org_id)


@router.get("/me", response_model=User)
def get_me(current_user: UserModel = Depends(get_current_user)):
    return current_user


@router.get("/", response_model=List[User])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    query = _filter_by_org(db.query(UserModel), current_user)
    return query.offset(skip).limit(limit).all()


@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    _require_admin(current_user)

    # 用户名冲突检查
    existing = db.query(UserModel).filter(UserModel.username == user_in.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在",
        )

    # org_id 策略：
    #   SUPER_ADMIN -> 可以指定任意 org_id
    #   ADMIN       -> 强制使用自己所在的 org_id，避免越权
    assigned_org_id = user_in.org_id
    if current_user.role != UserRole.SUPER_ADMIN:
        assigned_org_id = current_user.org_id
    else:
        # SUPER_ADMIN 必须显式指定 org_id，避免创建孤儿用户
        if assigned_org_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="必须指定组织",
            )

    # 角色不能被普通管理员提升到 SUPER_ADMIN
    assigned_role = user_in.role
    if assigned_role == UserRole.SUPER_ADMIN and current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅超级管理员可创建超级管理员账号",
        )

    db_user = UserModel(
        username=user_in.username,
        email=user_in.email,
        phone=user_in.phone,
        real_name=user_in.real_name,
        role=assigned_role,
        hashed_password=get_password_hash(user_in.password),
        org_id=assigned_org_id,
        is_active=user_in.is_active,
    )
    db.add(db_user)
    write_audit_log(
        db, request, current_user,
        action="create", target_type="user", target_id=None,
        new_value={
            "username": user_in.username,
            "email": user_in.email,
            "role": assigned_role.value if assigned_role else None,
            "org_id": assigned_org_id,
        },
    )
    db.commit()
    db.refresh(db_user)
    return db_user


@router.get("/{user_id}", response_model=User)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    query = _filter_by_org(db.query(UserModel), current_user)
    user = query.filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return user


@router.put("/{user_id}", response_model=User)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    _require_admin(current_user)

    query = _filter_by_org(db.query(UserModel), current_user)
    db_user = query.filter(UserModel.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    # 同级保护：非 SUPER_ADMIN 不能修改 ADMIN/SUPER_ADMIN 的信息
    if current_user.role != UserRole.SUPER_ADMIN and db_user.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改管理员账号")

    update_data = user_in.model_dump(exclude_unset=True)
    # 阻止普通管理员将角色提升到 SUPER_ADMIN
    if "role" in update_data and current_user.role != UserRole.SUPER_ADMIN:
        if update_data["role"] == UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="仅超级管理员可将角色提升为超级管理员",
            )
    # 非 SUPER_ADMIN 不能修改 org_id（避免越权转移租户）
    if "org_id" in update_data and current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权修改用户所属组织",
        )

    old_value = {
        "email": db_user.email,
        "phone": db_user.phone,
        "real_name": db_user.real_name,
        "role": db_user.role.value if db_user.role else None,
        "is_active": db_user.is_active,
        "org_id": db_user.org_id,
    }
    for key, value in update_data.items():
        setattr(db_user, key, value)

    write_audit_log(
        db, request, current_user,
        action="update", target_type="user", target_id=user_id,
        old_value=old_value,
        new_value=update_data,
    )
    db.commit()
    db.refresh(db_user)
    return db_user


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    _require_admin(current_user)

    query = _filter_by_org(db.query(UserModel), current_user)
    db_user = query.filter(UserModel.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if db_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己的账号",
        )
    # 同级保护：非 SUPER_ADMIN 不能删除 ADMIN/SUPER_ADMIN
    if current_user.role != UserRole.SUPER_ADMIN and db_user.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权删除管理员账号")

    old_value = {
        "username": db_user.username,
        "email": db_user.email,
        "role": db_user.role.value if db_user.role else None,
        "org_id": db_user.org_id,
    }
    db.delete(db_user)
    write_audit_log(
        db, request, current_user,
        action="delete", target_type="user", target_id=user_id,
        old_value=old_value,
    )
    db.commit()
    return {"message": "用户已删除"}
