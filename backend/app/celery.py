"""
Celery 配置 — 异步任务队列与定时调度。
- broker: Redis (从 settings.REDIS_URL 读取)
- backend: Redis (同 broker)
- 定时任务: 临期食材预警、低库存预警、每日财务汇总、审计日志清理、心跳
- 所有查询均注入 org_id 过滤（除 SUPER_ADMIN / ADMIN 全局汇总外）
"""
from __future__ import annotations

import logging
from celery import Celery
from celery.schedules import crontab
from datetime import datetime, timedelta, timezone
from sqlalchemy import func

from app.config import settings
from app.database import SessionLocal
from app.models import Ingredient, StockIn, StockOut, Organization, UserRole, AuditLog

logger = logging.getLogger(__name__)

celery_app = Celery(
    "school_food_chain",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.celery"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    # 与主应用保持一致：主应用 DateTime(timezone=True) 存储 UTC，
    # Celery 也应使用 UTC，避免定时任务时区错乱
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    # 任务重试策略
    task_default_retry_delay=60,        # 重试间隔 60 秒
    task_default_max_retries=3,         # 最多重试 3 次
    task_acks_late=True,                # 任务完成后才确认，避免崩溃丢失
    task_reject_on_worker_lost=True,    # worker 异常退出时拒绝任务，重新入队
)

# ---------------------------------------------------------------------------
# 定时任务
# ---------------------------------------------------------------------------
celery_app.conf.beat_schedule = {
    "check-expiry-every-6h": {
        "task": "app.celery.check_expiring_ingredients",
        "schedule": timedelta(hours=6),
        "args": (30,),
    },
    "check-low-stock-hourly": {
        "task": "app.celery.check_low_stock",
        "schedule": timedelta(hours=1),
    },
    "daily-finance-summary": {
        "task": "app.celery.daily_finance_summary",
        "schedule": crontab(hour=2, minute=0),
    },
    "daily-audit-cleanup": {
        "task": "app.celery.cleanup_audit_logs",
        "schedule": crontab(hour=3, minute=0),
        "args": (90,),
    },
    "heartbeat-every-5min": {
        "task": "app.celery.heartbeat",
        "schedule": timedelta(minutes=5),
    },
}


# ===========================================================================
# 任务实现
# ===========================================================================
@celery_app.task(
    bind=True,
    name="app.celery.check_expiring_ingredients",
    autoretry_for=(Exception,),
    retry_backoff=True,          # 指数退避
    retry_backoff_max=600,       # 最大退避 10 分钟
    retry_jitter=True,           # 添加随机抖动，避免任务同时重试
)
def check_expiring_ingredients(self, days: int = 30) -> dict:
    """扫描临期食材（含 org_id 字段）。"""
    cutoff = datetime.now(timezone.utc) + timedelta(days=days)
    now = datetime.now(timezone.utc)

    db = SessionLocal()
    try:
        records = (
            db.query(StockIn, Ingredient.name.label("ingredient_name"))
            .join(Ingredient, Ingredient.id == StockIn.ingredient_id)
            # 必须使用 SQLAlchemy 的 `.isnot(None)`/`.is_(True)`，不能用 Python 的 `is not None`
            .filter(StockIn.expiry_date.isnot(None))
            .filter(StockIn.expiry_date <= cutoff)
            .filter(StockIn.expiry_date >= now)
            .order_by(StockIn.expiry_date.asc())
            .all()
        )

        alerts = []
        for stock_in, name in records:
            days_left = (stock_in.expiry_date - now).days if stock_in.expiry_date else 0
            alerts.append({
                "batch_no": stock_in.batch_no,
                "ingredient_name": name or "未知",
                "ingredient_id": stock_in.ingredient_id,
                "org_id": stock_in.org_id,
                "quantity": stock_in.quantity,
                "unit_price": stock_in.unit_price,
                "expiry_date": stock_in.expiry_date.isoformat() if stock_in.expiry_date else None,
                "days_left": days_left,
            })
        return {
            "task": "check_expiring_ingredients",
            "alert_count": len(alerts),
            "generated_at": now.isoformat(),
            "items": alerts[:200],
        }
    except Exception:
        logger.exception("check_expiring_ingredients 执行失败")
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="app.celery.check_low_stock",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def check_low_stock(self) -> dict:
    """扫描所有组织低于安全库存的食材（全局预警）。"""
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        items = (
            db.query(Ingredient)
            .filter(Ingredient.is_active.is_(True))
            .filter(Ingredient.current_stock <= Ingredient.safety_stock)
            .all()
        )
        return {
            "task": "check_low_stock",
            "alert_count": len(items),
            "generated_at": now.isoformat(),
            "items": [
                {
                    "id": i.id,
                    "org_id": i.org_id,
                    "name": i.name,
                    "current": i.current_stock,
                    "safety": i.safety_stock,
                    "unit": i.unit,
                }
                for i in items
            ],
        }
    except Exception:
        logger.exception("check_low_stock 执行失败")
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="app.celery.daily_finance_summary",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def daily_finance_summary(self) -> dict:
    """昨日财务汇总（按组织分组）。"""
    now = datetime.now(timezone.utc)
    yesterday = now.date() - timedelta(days=1)
    # 使用范围查询走索引（避免 func.date() 全表扫描）
    y_start = datetime.combine(yesterday, datetime.min.time())
    y_end = datetime.combine(yesterday + timedelta(days=1), datetime.min.time())

    db = SessionLocal()
    try:
        # 按组织汇总昨日入库金额
        in_rows = (
            db.query(
                StockIn.org_id,
                func.coalesce(func.sum(StockIn.total_price), 0).label("total")
            )
            .filter(StockIn.created_at >= y_start)
            .filter(StockIn.created_at < y_end)
            .group_by(StockIn.org_id)
            .all()
        )

        # 按组织汇总昨日出库金额
        out_rows = (
            db.query(
                StockOut.org_id,
                func.coalesce(func.sum(StockOut.total_price), 0).label("total")
            )
            .filter(StockOut.created_at >= y_start)
            .filter(StockOut.created_at < y_end)
            .group_by(StockOut.org_id)
            .all()
        )

        org_ids = {r[0] for r in in_rows} | {r[0] for r in out_rows}
        org_map = {o.id: o.name for o in db.query(Organization).filter(Organization.id.in_(org_ids)).all()}

        org_summary = []
        for oid in org_ids:
            total_in = next((r[1] for r in in_rows if r[0] == oid), 0)
            total_out = next((r[1] for r in out_rows if r[0] == oid), 0)
            org_summary.append({
                "org_id": oid,
                "org_name": org_map.get(oid, f"组织#{oid}"),
                "total_in": float(total_in),
                "total_out": float(total_out),
                "balance": float(total_in - total_out),
            })

        return {
            "task": "daily_finance_summary",
            "date": yesterday.isoformat(),
            "org_count": len(org_summary),
            "generated_at": now.isoformat(),
            "orgs": org_summary,
        }
    except Exception:
        logger.exception("daily_finance_summary 执行失败")
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="app.celery.cleanup_audit_logs",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def cleanup_audit_logs(self, retention_days: int = 90) -> dict:
    """清理超过保留天数的审计日志。"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    db = SessionLocal()
    try:
        deleted = (
            db.query(AuditLog)
            .filter(AuditLog.created_at < cutoff)
            .delete(synchronize_session=False)
        )
        try:
            db.commit()
        except Exception:
            logger.exception("cleanup_audit_logs 提交事务失败")
            db.rollback()
            raise
        return {
            "task": "cleanup_audit_logs",
            "retention_days": retention_days,
            "deleted_count": deleted,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception:
        logger.exception("cleanup_audit_logs 执行失败")
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(bind=True, name="app.celery.heartbeat")
def heartbeat(self) -> dict:
    """Celery Worker 心跳，用于健康检查。"""
    return {
        "task": "heartbeat",
        "status": "ok",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ===========================================================================
# UserRole 在此模块内也能使用（部分场景可能需要）
# ===========================================================================
__all__ = ["celery_app", "UserRole"]
