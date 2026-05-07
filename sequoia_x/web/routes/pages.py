"""HTML 页面路由。"""

from fastapi import APIRouter, Request

from sequoia_x.web.services import STRATEGY_META

router = APIRouter()


@router.get("/")
async def index(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request=request, name="index.html",
        context={"strategies": request.app.state.services.list_strategies()},
    )


@router.get("/strategy/{key}")
async def strategy_detail(key: str, request: Request):
    templates = request.app.state.templates
    if key not in STRATEGY_META:
        return templates.TemplateResponse(
            request=request, name="index.html",
            context={"strategies": request.app.state.services.list_strategies(), "error": f"未知策略: {key}"},
        )
    meta = STRATEGY_META[key]
    services = request.app.state.services
    return templates.TemplateResponse(
        request=request, name="strategy_detail.html",
        context={
            "key": key,
            "meta": meta,
            "strategy": next(s for s in services.list_strategies() if s["key"] == key),
            "results": services.get_cached_results(key),
        },
    )


@router.get("/config")
async def config_page(request: Request):
    templates = request.app.state.templates
    settings = request.app.state.settings
    return templates.TemplateResponse(
        request=request, name="config.html",
        context={"settings": settings, "strategies": STRATEGY_META},
    )


@router.get("/stocks")
async def stocks_page(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request=request, name="stock_browser.html",
        context={},
    )


@router.get("/system")
async def system_page(request: Request):
    templates = request.app.state.templates
    services = request.app.state.services
    info = services.get_system_info()
    logs = services.get_recent_logs(request.app.state.log_handler, limit=50)
    return templates.TemplateResponse(
        request=request, name="system.html",
        context={"info": info, "logs": logs},
    )
