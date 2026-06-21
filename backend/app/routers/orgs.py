"""Organizations router — 仅 SUPER_ADMIN 可管理组织（组织是跨租户元数据）"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.auth import require_roles
from app.models import (
    Organization, User, UserRole,
    Supplier as SupplierModel,
    Ingredient as IngredientModel,
    StockIn as StockInModel,
)
from app.schemas import OrgCreate, OrgUpdate, Org
from app.audit_utils import write_audit_log

router = APIRouter()


@router.get("/", response_model=List[Org])
def list_orgs(
    skip: int = 0,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN)),
):
    return db.query(Organization).offset(skip).limit(limit).all()


@router.post("/", response_model=Org)
def create_org(
    org: OrgCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN)),
):
    # 校验 code 唯一
    if org.code and db.query(Organization).filter(Organization.code == org.code).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="组织编码已存在")
    # 校验 parent_id 存在
    if org.parent_id is not None:
        if not db.query(Organization).filter(Organization.id == org.parent_id).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="父组织不存在")
    db_org = Organization(**org.model_dump())
    db.add(db_org)
    write_audit_log(
        db, request, current_user,
        action="create", target_type="org", target_id=None,
        new_value=org.model_dump(),
    )
    db.commit()
    db.refresh(db_org)
    return db_org


@router.get("/{org_id}", response_model=Org)
def get_org(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN)),
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="组织不存在")
    return org


@router.put("/{org_id}", response_model=Org)
def update_org(
    org_id: int,
    org: OrgUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN)),
):
    db_org = db.query(Organization).filter(Organization.id == org_id).first()
    if not db_org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="组织不存在")

    update_data = org.model_dump(exclude_unset=True)

    # 深层循环检测：沿 parent 链向上遍历
    if "parent_id" in update_data and update_data["parent_id"] is not None:
        new_parent_id = update_data["parent_id"]
        if new_parent_id == org_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="组织不能将自己设为父组织")
        # 校验父组织存在
        if not db.query(Organization).filter(Organization.id == new_parent_id).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="父组织不存在")
        # 沿 parent 链向上遍历，检测间接环
        visited = {org_id}
        ancestor_id = new_parent_id
        while ancestor_id is not None:
            if ancestor_id in visited:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="组织层级存在循环引用",
                )
            visited.add(ancestor_id)
            ancestor = db.query(Organization).filter(Organization.id == ancestor_id).first()
            if not ancestor:
                break
            ancestor_id = ancestor.parent_id

    old_value = {
        "name": db_org.name,
        "address": db_org.address,
        "contact_person": db_org.contact_person,
        "contact_phone": db_org.contact_phone,
        "license_no": db_org.license_no,
        "is_active": db_org.is_active,
        "parent_id": db_org.parent_id,
    }
    for key, value in update_data.items():
        setattr(db_org, key, value)

    write_audit_log(
        db, request, current_user,
        action="update", target_type="org", target_id=org_id,
        old_value=old_value,
        new_value=update_data,
    )
    db.commit()
    db.refresh(db_org)
    return db_org


@router.delete("/{org_id}")
def delete_org(
    org_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN)),
):
    db_org = db.query(Organization).filter(Organization.id == org_id).first()
    if not db_org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="组织不存在")
    # 阻止删除非空组织（有用户或子组织）
    if db.query(User).filter(User.org_id == org_id).count() > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="组织下仍有用户，无法删除")
    if db.query(Organization).filter(Organization.parent_id == org_id).count() > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="组织下仍有子组织，无法删除")
    # 检查更多关联：供应商、食材、入库记录
    if db.query(SupplierModel).filter(SupplierModel.org_id == org_id).count() > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="组织下仍有供应商，无法删除")
    if db.query(IngredientModel).filter(IngredientModel.org_id == org_id).count() > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="组织下仍有食材，无法删除")
    if db.query(StockInModel).filter(StockInModel.org_id == org_id).count() > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="组织下仍有入库记录，无法删除")

    old_value = {
        "name": db_org.name,
        "code": db_org.code,
        "org_type": db_org.org_type.value if db_org.org_type else None,
        "parent_id": db_org.parent_id,
    }
    db.delete(db_org)
    write_audit_log(
        db, request, current_user,
        action="delete", target_type="org", target_id=org_id,
        old_value=old_value,
    )
    db.commit()
    return {"message": "组织已删除"}
