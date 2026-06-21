"""
WebSocket 实时推送 — 基于 Redis Pub/Sub 的多 Worker 广播。

架构:
  - 每个 FastAPI Worker 维护自己的 WebSocket 连接池（进程内）
  - 写操作（入库/出库/盘点/黑名单）通过 publish_event 发布到 Redis
  - 每个 Worker 的 Redis 订阅器收到消息后广播给本进程的 WebSocket 客户端
  - 客户端按 org_id 订阅，只收到本组织的告警

频道设计:
  - 全局频道: "ws:broadcast" — 所有客户端都收到
  - 组织频道: "ws:org:{org_id}" — 仅该组织成员收到
  - 角色频道: "ws:role:{role}" — 仅该角色收到（如 super_admin 收到所有告警）

消息格式:
  {
    "type": "alert" | "notification" | "data_update",
    "event": "low_stock" | "expiry" | "blacklist" | "stock_in" | ...,
    "org_id": 1,
    "title": "库存预警",
    "message": "大米库存不足",
    "level": "info" | "warning" | "critical",
    "data": {...},
    "timestamp": "2026-01-01T12:00:00Z"
  }
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.auth import decode_token
from app.redis_client import get_redis

logger = logging.getLogger(__name__)

router = APIRouter()

# Redis Pub/Sub 频道前缀
CHANNEL_BROADCAST = "ws:broadcast"
CHANNEL_ORG_PREFIX = "ws:org:"
CHANNEL_ROLE_PREFIX = "ws:role:"


# ---------------------------------------------------------------------------
# 连接管理器 — 每个进程独立维护
# ---------------------------------------------------------------------------
class ConnectionManager:
    """管理本进程的 WebSocket 连接，按 org_id 分组。"""

    def __init__(self) -> None:
        # org_id -> set of WebSocket
        self._connections: Dict[int, Set[WebSocket]] = {}
        # super_admin 连接（跨组织接收）
        self._global_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, org_id: int, is_super_admin: bool) -> None:
        await websocket.accept()
        async with self._lock:
            if is_super_admin:
                self._global_connections.add(websocket)
            else:
                self._connections.setdefault(org_id, set()).add(websocket)
        logger.debug("WebSocket connected: org_id=%d super_admin=%s", org_id, is_super_admin)

    async def disconnect(self, websocket: WebSocket, org_id: int, is_super_admin: bool) -> None:
        async with self._lock:
            if is_super_admin:
                self._global_connections.discard(websocket)
            else:
                conns = self._connections.get(org_id)
                if conns:
                    conns.discard(websocket)
                    if not conns:
                        del self._connections[org_id]
        logger.debug("WebSocket disconnected: org_id=%d", org_id)

    async def broadcast_to_org(self, org_id: int, message: dict) -> None:
        """广播给指定组织的所有连接 + 所有 super_admin。"""
        async with self._lock:
            targets = set(self._global_connections)
            targets.update(self._connections.get(org_id, set()))

        text = json.dumps(message, default=str)
        dead = []
        for ws in targets:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_text(text)
            except Exception:
                dead.append(ws)

        # 清理断开的连接
        if dead:
            async with self._lock:
                for ws in dead:
                    self._global_connections.discard(ws)
                    for conns in self._connections.values():
                        conns.discard(ws)

    async def broadcast_all(self, message: dict) -> None:
        """广播给所有连接。"""
        async with self._lock:
            targets = set(self._global_connections)
            for conns in self._connections.values():
                targets.update(conns)

        text = json.dumps(message, default=str)
        dead = []
        for ws in targets:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_text(text)
            except Exception:
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    self._global_connections.discard(ws)
                    for conns in self._connections.values():
                        conns.discard(ws)


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# 事件发布 — 供业务代码调用
# ---------------------------------------------------------------------------
def publish_event(
    event: str,
    org_id: Optional[int],
    title: str,
    message: str,
    level: str = "info",
    data: Optional[dict] = None,
    target_role: Optional[str] = None,
) -> None:
    """发布实时事件到 Redis Pub/Sub。

    Args:
        event: 事件类型（low_stock / expiry / blacklist / stock_in / stock_out / inventory_check）
        org_id: 目标组织 ID（None 表示全局）
        title: 标题
        message: 内容
        level: info / warning / critical
        data: 附加数据
        target_role: 目标角色（None 表示按 org_id 广播）
    """
    payload = {
        "type": "notification",
        "event": event,
        "org_id": org_id,
        "title": title,
        "message": message,
        "level": level,
        "data": data or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    redis = get_redis()
    if redis is None:
        # Redis 不可用时，同步路由无法直接 await 广播，仅记录日志
        logger.debug("Event (Redis unavailable, skipped): %s - %s", event, title)
        return

    try:
        channel = CHANNEL_BROADCAST
        if target_role:
            channel = f"{CHANNEL_ROLE_PREFIX}{target_role}"
        elif org_id is not None:
            channel = f"{CHANNEL_ORG_PREFIX}{org_id}"
        redis.publish(channel, json.dumps(payload, default=str))
    except Exception as e:
        logger.warning("Failed to publish event: %s", e)


def publish_low_stock_alert(ingredient_name: str, current_stock, safety_stock, unit: str, org_id: int) -> None:
    """发布低库存预警。"""
    level = "critical" if float(current_stock) <= 0 else "warning"
    publish_event(
        event="low_stock",
        org_id=org_id,
        title="库存预警",
        message=f"{ingredient_name} 当前库存 {current_stock}{unit}，低于安全库存 {safety_stock}{unit}",
        level=level,
        data={"ingredient_name": ingredient_name, "current_stock": float(current_stock),
              "safety_stock": float(safety_stock), "unit": unit},
    )


def publish_expiry_alert(ingredient_name: str, batch_no: str, days_left: int, org_id: int) -> None:
    """发布临期预警。"""
    level = "critical" if days_left <= 7 else "warning"
    publish_event(
        event="expiry",
        org_id=org_id,
        title="临期预警",
        message=f"{ingredient_name}（批次 {batch_no}）将于 {days_left} 天后过期",
        level=level,
        data={"ingredient_name": ingredient_name, "batch_no": batch_no, "days_left": days_left},
    )


def publish_blacklist_alert(supplier_name: str, reason: str, org_id: int) -> None:
    """发布供应商黑名单告警。"""
    publish_event(
        event="blacklist",
        org_id=org_id,
        title="供应商黑名单告警",
        message=f"供应商 {supplier_name} 已被列入黑名单，原因：{reason}",
        level="critical",
        data={"supplier_name": supplier_name, "reason": reason},
    )


def publish_stock_update(action: str, ingredient_name: str, quantity, org_id: int) -> None:
    """发布库存变更通知。"""
    publish_event(
        event=action,
        org_id=org_id,
        title="库存变更",
        message=f"{ingredient_name} {action == 'stock_in' and '入库' or '出库'} {quantity}",
        level="info",
        data={"action": action, "ingredient_name": ingredient_name, "quantity": float(quantity)},
    )


# ---------------------------------------------------------------------------
# Redis 订阅器 — 后台线程监听 Pub/Sub 并广播到本进程的 WebSocket
# ---------------------------------------------------------------------------
_subscriber_started = False


def start_redis_subscriber() -> None:
    """启动 Redis 订阅后台线程（仅启动一次）。"""
    global _subscriber_started
    if _subscriber_started:
        return
    _subscriber_started = True

    def _subscribe_loop():
        import time
        while True:
            redis = get_redis()
            if redis is None:
                time.sleep(5)
                continue

            try:
                pubsub = redis.pubsub()
                pubsub.psubscribe(f"{CHANNEL_ORG_PREFIX}*", CHANNEL_BROADCAST, f"{CHANNEL_ROLE_PREFIX}*")
                logger.info("WebSocket Redis subscriber started")

                for message in pubsub.listen():
                    if message["type"] != "pmessage":
                        continue
                    try:
                        data = message["data"]
                        if isinstance(data, bytes):
                            data = data.decode("utf-8")
                        payload = json.loads(data)
                        # 在事件循环中广播
                        org_id = payload.get("org_id")
                        if org_id:
                            asyncio.run(manager.broadcast_to_org(org_id, payload))
                        else:
                            asyncio.run(manager.broadcast_all(payload))
                    except Exception as e:
                        logger.warning("Failed to process WS message: %s", e)
            except Exception as e:
                logger.warning("Redis subscriber error, reconnecting in 5s: %s", e)
                time.sleep(5)

    thread = threading.Thread(target=_subscribe_loop, daemon=True, name="ws-redis-subscriber")
    thread.start()


# ---------------------------------------------------------------------------
# WebSocket 端点
# ---------------------------------------------------------------------------
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 端点 — 通过 query 参数传 access_token 认证。

    用法:
      ws://host:8000/api/v1/ws?token=<access_token>
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="缺少 token 参数")
        return

    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        await websocket.close(code=4001, reason="token 无效或已过期")
        return

    user_id = payload.get("sub")
    if user_id is None:
        await websocket.close(code=4001, reason="token 无效")
        return

    # 查询用户信息获取 org_id 和 role
    from app.database import SessionLocal
    from app.models import User, UserRole
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_active:
            await websocket.close(code=4003, reason="用户不存在或已禁用")
            return

        org_id = user.org_id or 0
        is_super_admin = user.role == UserRole.SUPER_ADMIN
    finally:
        db.close()

    await manager.connect(websocket, org_id, is_super_admin)

    # 发送连接成功消息
    await websocket.send_text(json.dumps({
        "type": "connected",
        "message": "WebSocket 连接成功",
        "org_id": org_id,
    }))

    try:
        while True:
            # 保持连接，接收客户端心跳
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket, org_id, is_super_admin)
