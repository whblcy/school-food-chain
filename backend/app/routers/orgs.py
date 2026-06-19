"""Organizations router"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.auth import get_current_user
from app.models import Organization, User
from app.schemas import OrgCreate, Org

router = APIRouter()


@router.get("/", response_model=List[Org])
def list_orgs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    orgs = db.query(Organization).offset(skip).limit(limit).all()
    return orgs


@router.post("/", response_model=Org)
def create_org(
    org: OrgCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_org = Organization(**org.dict())
    db.add(db_org)
    db.commit()
    db.refresh(db_org)
    return db_org


@router.get("/{org_id}", response_model=Org)
def get_org(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.put("/{org_id}", response_model=Org)
def update_org(
    org_id: int,
    org: OrgCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_org = db.query(Organization).filter(Organization.id == org_id).first()
    if not db_org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    for key, value in org.dict().items():
        setattr(db_org, key, value)
    
    db.commit()
    db.refresh(db_org)
    return db_org


@router.delete("/{org_id}")
def delete_org(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_org = db.query(Organization).filter(Organization.id == org_id).first()
    if not db_org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    db.delete(db_org)
    db.commit()
    return {"message": "Organization deleted"}
