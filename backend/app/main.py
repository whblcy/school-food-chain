"""
School Food Chain - FastAPI Backend
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.routers import auth, users, orgs, suppliers, ingredients, stock, finance, reports, trace, audit

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="School Food Chain API",
    description="学校食堂食材全链路管理平台",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/v1/users", tags=["用户"])
app.include_router(orgs.router, prefix="/api/v1/orgs", tags=["组织"])
app.include_router(suppliers.router, prefix="/api/v1/suppliers", tags=["供应商"])
app.include_router(ingredients.router, prefix="/api/v1/ingredients", tags=["食材"])
app.include_router(stock.router, prefix="/api/v1/stock", tags=["库存"])
app.include_router(finance.router, prefix="/api/v1/finance", tags=["财务"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["报表"])
app.include_router(trace.router, prefix="/api/v1/trace", tags=["追溯"])
app.include_router(audit.router, prefix="/api/v1/audit", tags=["审计"])


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}
