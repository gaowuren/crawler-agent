"""FastAPI：表单提交 URL，后台抓取并写入 MongoDB。"""

from __future__ import annotations

import traceback
from contextlib import asynccontextmanager
from pathlib import Path

from bson import ObjectId
from fastapi import BackgroundTasks, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from src import config
from src.crawl_core import is_chinanews_url, run_list_crawl_gen, run_single_article
from src import mongo_store

ROOT = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(ROOT / "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Mongo 未启动时不阻塞整站：仍可打开说明页，提交时再提示
    app.state.mongo_ok = mongo_store.try_init_mongodb()
    yield


app = FastAPI(title="spider_agent", lifespan=lifespan)


def _mongo_ok(request: Request) -> bool:
    return bool(getattr(request.app.state, "mongo_ok", False))


def _recent_jobs_safe(request: Request) -> list[dict]:
    if not _mongo_ok(request):
        return []
    try:
        return [
            mongo_store.job_to_api(j) for j in mongo_store.list_recent_jobs(15)
        ]
    except Exception:
        return []


def _run_list_job(job_id: str, start_url: str, max_pages: int, max_articles: int, interval: float) -> None:
    oid = ObjectId(job_id)
    mongo_store.mark_job_running(oid)
    try:
        articles = list(
            run_list_crawl_gen(
                start_url,
                max_pages=max_pages,
                max_articles=max_articles,
                interval=interval,
            )
        )
        mongo_store.insert_articles(oid, articles)
        mongo_store.update_job(oid, "done")
    except Exception as exc:
        mongo_store.update_job(
            oid, "failed", error_message=f"{exc}\n{traceback.format_exc()}"
        )


def _run_single_job(job_id: str, url: str, interval: float) -> None:
    oid = ObjectId(job_id)
    mongo_store.mark_job_running(oid)
    try:
        rec = run_single_article(url, interval=interval, referer=url)
        mongo_store.insert_articles(oid, [rec])
        mongo_store.update_job(oid, "done")
    except Exception as exc:
        mongo_store.update_job(
            oid, "failed", error_message=f"{exc}\n{traceback.format_exc()}"
        )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    mongo_ok = _mongo_ok(request)
    mongo_banner = None
    if not mongo_ok:
        mongo_banner = (
            "当前无法连接 MongoDB（常见原因：未启动容器）。请在项目根目录执行 "
            "<code>docker compose up -d</code>，等待几秒后<strong>重启</strong> "
            "<code>uvicorn</code>；或确认 <code>MONGODB_URI</code> 指向正确地址。"
        )
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "jobs": _recent_jobs_safe(request),
            "default_start": config.DEFAULT_START_URL,
            "form_values": {},
            "mongo_banner": mongo_banner,
        },
    )


@app.post("/crawl", response_class=HTMLResponse)
async def crawl_submit(
    request: Request,
    background_tasks: BackgroundTasks,
    mode: str = Form("single"),
    start_url: str = Form(...),
    max_pages: int = Form(1),
    max_articles: int = Form(10),
    interval: float = Form(1.5),
) -> HTMLResponse:
    start_url = (start_url or "").strip()
    if not start_url:
        raise HTTPException(status_code=400, detail="请输入网址")

    mode = mode.strip().lower()
    if mode not in ("single", "list"):
        mode = "single"

    if mode == "list" and not is_chinanews_url(start_url):
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "jobs": _recent_jobs_safe(request),
                "default_start": config.DEFAULT_START_URL,
                "error": "列表爬取仅支持中国新闻网相关域名（首页 / 频道页）。任意站点请选「单页抓取」。",
                "form_values": {
                    "mode": mode,
                    "start_url": start_url,
                    "max_pages": max_pages,
                    "max_articles": max_articles,
                    "interval": interval,
                },
                "mongo_banner": None
                if _mongo_ok(request)
                else (
                    "当前无法连接 MongoDB。请执行 <code>docker compose up -d</code> 后重启 uvicorn。"
                ),
            },
            status_code=400,
        )

    if not _mongo_ok(request):
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "jobs": _recent_jobs_safe(request),
                "default_start": config.DEFAULT_START_URL,
                "error": "无法写入数据库：MongoDB 未就绪。请先 <code>docker compose up -d</code>，再重启本 Web 服务。",
                "form_values": {
                    "mode": mode,
                    "start_url": start_url,
                    "max_pages": max_pages,
                    "max_articles": max_articles,
                    "interval": interval,
                },
                "mongo_banner": (
                    "无法连接 MongoDB。请在项目根目录执行 <code>docker compose up -d</code>，"
                    "确认 <code>docker ps</code> 中有 mongo 容器后重启 <code>uvicorn</code>。"
                ),
            },
            status_code=503,
        )

    params = {
        "max_pages": max_pages,
        "max_articles": max_articles,
        "interval": interval,
    }
    job_oid = mongo_store.insert_job(start_url, mode, params)
    job_id = str(job_oid)

    if mode == "list":
        background_tasks.add_task(
            _run_list_job, job_id, start_url, max_pages, max_articles, interval
        )
    else:
        background_tasks.add_task(_run_single_job, job_id, start_url, interval)

    jobs = _recent_jobs_safe(request)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "jobs": jobs,
            "default_start": config.DEFAULT_START_URL,
            "message": f"已创建任务 {job_id}，后台抓取中。可刷新本页或访问 /api/jobs/{job_id} 查看状态。",
            "last_job_id": job_id,
            "form_values": {
                "mode": mode,
                "start_url": start_url,
                "max_pages": max_pages,
                "max_articles": max_articles,
                "interval": interval,
            },
            "mongo_banner": None,
        },
    )


@app.get("/api/jobs/{job_id}")
async def api_get_job(request: Request, job_id: str) -> JSONResponse:
    if not _mongo_ok(request):
        raise HTTPException(
            status_code=503,
            detail="MongoDB unavailable; run docker compose up -d and restart uvicorn",
        )
    try:
        oid = mongo_store.parse_object_id(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    doc = mongo_store.get_job(oid)
    if doc is None:
        raise HTTPException(status_code=404, detail="job not found")
    return JSONResponse(mongo_store.job_to_api(doc))


@app.get("/api/jobs/{job_id}/articles")
async def api_job_articles(
    request: Request, job_id: str, limit: int = 50
) -> JSONResponse:
    if not _mongo_ok(request):
        raise HTTPException(
            status_code=503,
            detail="MongoDB unavailable; run docker compose up -d and restart uvicorn",
        )
    try:
        oid = mongo_store.parse_object_id(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if mongo_store.get_job(oid) is None:
        raise HTTPException(status_code=404, detail="job not found")
    cur = (
        mongo_store.get_db()
        .crawl_articles.find({"job_id": oid})
        .sort("created_at", -1)
        .limit(min(limit, 200))
    )
    out = []
    for doc in cur:
        d = dict(doc)
        d.pop("_id", None)
        d["job_id"] = str(d["job_id"])
        if d.get("created_at") is not None:
            d["created_at"] = d["created_at"].isoformat()
        out.append(d)
    return JSONResponse({"items": out, "count": len(out)})
