"""MongoDB：任务与文章集合，供 Web / 后台任务写入。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ASCENDING, MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError

from src import config

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(
            config.MONGODB_URI,
            serverSelectionTimeoutMS=config.MONGODB_SERVER_SELECTION_TIMEOUT_MS,
        )
    return _client


def try_init_mongodb() -> bool:
    """连接 Mongo 并建索引；失败时关闭客户端，返回 False（不抛异常）。"""
    global _client
    try:
        if _client is not None:
            try:
                _client.admin.command("ping")
            except PyMongoError:
                try:
                    _client.close()
                except Exception:
                    pass
                _client = None
        client = get_client()
        client.admin.command("ping")
        ensure_indexes()
        return True
    except PyMongoError:
        if _client is not None:
            try:
                _client.close()
            except Exception:
                pass
        _client = None
        return False


def get_db():
    return get_client()[config.MONGODB_DB]


def ensure_indexes() -> None:
    db = get_db()
    db.crawl_jobs.create_index([("created_at", -1)])
    db.crawl_articles.create_index(
        [("job_id", ASCENDING), ("url", ASCENDING)], unique=True
    )


def insert_job(input_url: str, mode: str, params: dict[str, Any]) -> ObjectId:
    doc: dict[str, Any] = {
        "input_url": input_url,
        "mode": mode,
        "status": "pending",
        "error_message": None,
        "created_at": datetime.now(timezone.utc),
        "finished_at": None,
        "params": params,
    }
    return get_db().crawl_jobs.insert_one(doc).inserted_id


def mark_job_running(job_id: ObjectId) -> None:
    get_db().crawl_jobs.update_one({"_id": job_id}, {"$set": {"status": "running"}})


def update_job(
    job_id: ObjectId, status: str, error_message: str | None = None
) -> None:
    patch: dict[str, Any] = {
        "status": status,
        "finished_at": datetime.now(timezone.utc),
    }
    if error_message is not None:
        patch["error_message"] = error_message
    else:
        patch["error_message"] = None
    get_db().crawl_jobs.update_one({"_id": job_id}, {"$set": patch})


def insert_articles(job_id: ObjectId, articles: list[dict[str, Any]]) -> int:
    if not articles:
        return 0
    now = datetime.now(timezone.utc)
    col = get_db().crawl_articles
    n = 0
    for a in articles:
        doc = dict(a)
        doc["job_id"] = job_id
        doc["created_at"] = now
        doc.pop("_id", None)
        try:
            col.insert_one(doc)
            n += 1
        except DuplicateKeyError:
            continue
    return n


def get_job(job_id: ObjectId) -> dict[str, Any] | None:
    return get_db().crawl_jobs.find_one({"_id": job_id})


def list_recent_jobs(limit: int = 20) -> list[dict[str, Any]]:
    cur = (
        get_db()
        .crawl_jobs.find()
        .sort("created_at", -1)
        .limit(limit)
    )
    return list(cur)


def job_to_api(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if doc is None:
        return None
    out = dict(doc)
    oid = out.pop("_id")
    out["id"] = str(oid)
    for key in ("created_at", "finished_at"):
        if out.get(key) is not None:
            out[key] = out[key].isoformat()
    return out


def parse_object_id(job_id: str) -> ObjectId:
    try:
        return ObjectId(job_id)
    except InvalidId as exc:
        raise ValueError("invalid job id") from exc
