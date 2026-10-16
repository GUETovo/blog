"""音乐接口：代理公共 meting 服务，给前端 /api/music 提供歌单。

背景：前端 components/providers/MusicProvider.tsx 会请求
    GET /api/music?id=<歌单ID>     或     GET /api/music?ids=<歌曲ID,逗号分隔>
但上游后端没有这个路由（router.py 注册的 16 个 router 里没有 music），
而 Nginx 把 /api/ 全部转发给 FastAPI，所以前端只会拿到 404，音乐永远播不了。
本模块补上这个缺口。

返回格式刻意保持与 meting 一致（name / artist / url / pic / lrc / id），
因为前端就是这么映射的：title||name、cover||pic、src||url、lrcUrl||lrc。
"""

import time

import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/music", tags=["音乐"])

# 公共 meting 服务，按顺序尝试（这类公共服务会挂，多备几个）
METING_ENDPOINTS = [
    "https://api.injahow.cn/meting/",
    "https://api.qijieya.cn/meting/",
]
REQUEST_TIMEOUT = 15.0
CACHE_TTL = 600  # 秒；歌单不常变，缓存 10 分钟，避免每次进页面都打公共服务

_cache: dict[str, tuple[float, list]] = {}


def _cache_get(key: str):
    item = _cache.get(key)
    if not item:
        return None
    ts, data = item
    if time.time() - ts > CACHE_TTL:
        _cache.pop(key, None)
        return None
    return data


async def _try_fetch(endpoint: str, params: dict):
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
        resp = await client.get(endpoint, params=params)
        resp.raise_for_status()
        data = resp.json()
    if isinstance(data, list) and data:
        return data
    return None


@router.get("")
async def get_music(
    id: str | None = Query(None, description="歌单 ID"),
    ids: str | None = Query(None, description="歌曲 ID，逗号分隔"),
    server: str = Query("netease", description="netease / tencent / kugou / xiami"),
    meting_type: str | None = Query(None, alias="type", description="覆盖 meting 的 type"),
):
    if not id and not ids:
        raise HTTPException(400, "需要提供 id（歌单）或 ids（歌曲列表）")

    if id:
        params = {"server": server, "type": meting_type or "playlist", "id": id}
    else:
        params = {"server": server, "type": meting_type or "song", "id": ids}

    cache_key = f"{server}|{params['type']}|{params['id']}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    errors = []
    for endpoint in METING_ENDPOINTS:
        try:
            data = await _try_fetch(endpoint, params)
            if data:
                _cache[cache_key] = (time.time(), data)
                return data
            errors.append(f"{endpoint} 返回空")
        except Exception as exc:  # noqa: BLE001 - 公共服务不可控，逐个降级
            errors.append(f"{endpoint} 失败: {exc}")

    raise HTTPException(502, "所有 meting 服务都不可用 → " + " | ".join(errors))
