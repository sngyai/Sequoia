"""JSON API 路由。"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from sequoia_x.web.services import STRATEGY_META, TaskStatus

router = APIRouter()


# ---------------------------------------------------------------------------
# Strategy endpoints
# ---------------------------------------------------------------------------

@router.get("/strategies")
async def list_strategies(request: Request):
    services = request.app.state.services
    return {"strategies": services.list_strategies()}


@router.post("/strategies/{key}/run")
async def run_strategy(key: str, request: Request):
    services = request.app.state.services
    if key not in STRATEGY_META:
        raise HTTPException(404, f"未知策略: {key}")
    task_id = services.run_strategy_async(key)
    return {"task_id": task_id, "status": TaskStatus.PENDING}


@router.get("/tasks/{task_id}")
async def get_task(task_id: str, request: Request):
    services = request.app.state.services
    record = services.get_task_status(task_id)
    if record is None:
        raise HTTPException(404, f"任务不存在: {task_id}")
    return {
        "task_id": record.task_id,
        "strategy_key": record.strategy_key,
        "status": record.status,
        "started_at": record.started_at.isoformat() if record.started_at else None,
        "finished_at": record.finished_at.isoformat() if record.finished_at else None,
        "result_count": len(record.results),
        "results": record.results,
        "error": record.error,
    }


@router.get("/strategies/{key}/results")
async def get_strategy_results(key: str, request: Request):
    services = request.app.state.services
    if key not in STRATEGY_META:
        raise HTTPException(404, f"未知策略: {key}")
    results = services.get_cached_results(key)
    return {"key": key, "results": results, "count": len(results)}


# ---------------------------------------------------------------------------
# Stock endpoints
# ---------------------------------------------------------------------------

@router.get("/stocks/search")
async def search_stocks(q: str, request: Request):
    services = request.app.state.services
    symbols = services.search_symbols(q)
    return {"symbols": symbols}


@router.get("/stocks/{symbol}")
async def get_stock(symbol: str, request: Request, days: int = 120):
    services = request.app.state.services
    data = services.get_stock_data(symbol, days)
    return {"symbol": symbol, "data": data}


@router.get("/stocks/{symbol}/summary")
async def get_stock_summary(symbol: str, request: Request):
    services = request.app.state.services
    summary = services.get_stock_summary(symbol)
    if summary is None:
        raise HTTPException(404, f"未找到股票: {symbol}")
    return summary


# ---------------------------------------------------------------------------
# System endpoints
# ---------------------------------------------------------------------------

@router.get("/system")
async def get_system(request: Request):
    services = request.app.state.services
    return services.get_system_info()


@router.get("/system/logs")
async def get_logs(request: Request, limit: int = 100):
    handler = request.app.state.log_handler
    services = request.app.state.services
    return {"logs": services.get_recent_logs(handler, limit)}


@router.post("/system/sync")
async def sync_data(request: Request):
    services = request.app.state.services
    task_id = services.sync_data_async()
    return {"task_id": task_id, "status": TaskStatus.PENDING}


@router.post("/system/backfill")
async def backfill_data(request: Request):
    services = request.app.state.services
    task_id = services.backfill_async()
    return {"task_id": task_id, "status": TaskStatus.PENDING}


# ---------------------------------------------------------------------------
# Config endpoints
# ---------------------------------------------------------------------------

@router.get("/config")
async def get_config(request: Request):
    settings = request.app.state.settings
    return {
        "feishu_webhook_url": settings.feishu_webhook_url,
        "strategy_webhooks": settings.strategy_webhooks,
        "db_path": settings.db_path,
        "start_date": settings.start_date,
    }


class ConfigUpdate(BaseModel):
    feishu_webhook_url: str | None = None
    strategy_webhooks: dict[str, str] | None = None


@router.put("/config")
async def update_config(body: ConfigUpdate, request: Request):
    from sequoia_x.web.env_writer import write_env, reload_settings

    updates: dict[str, str] = {}
    if body.feishu_webhook_url is not None:
        updates["FEISHU_WEBHOOK_URL"] = body.feishu_webhook_url
    if body.strategy_webhooks is not None:
        for key, url in body.strategy_webhooks.items():
            updates[f"STRATEGY_WEBHOOK_{key.upper()}"] = url

    if not updates:
        return {"ok": True, "message": "无需更新"}

    write_env(updates)
    new_settings = reload_settings()
    request.app.state.settings = new_settings
    request.app.state.services.settings = new_settings
    return {"ok": True, "message": "配置已更新"}


class WebhookTest(BaseModel):
    url: str


@router.post("/config/test-webhook")
async def test_webhook(body: WebhookTest):
    import asyncio
    import requests as req

    def _do_test() -> dict:
        payload = {"msg_type": "text", "content": {"text": "Sequoia-X Webhook Test - OK"}}
        try:
            resp = req.post(body.url, json=payload, timeout=10)
            data = resp.json()
            return {
                "ok": resp.status_code == 200 and data.get("code") == 0,
                "status_code": resp.status_code,
                "feishu_code": data.get("code"),
                "message": data.get("msg", ""),
            }
        except Exception as e:
            return {"ok": False, "status_code": 0, "feishu_code": -1, "message": str(e)}

    result = await asyncio.to_thread(_do_test)
    return result
