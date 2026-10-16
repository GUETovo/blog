"""图片上传：优先腾讯云 COS，未配置 COS 时自动落到服务器本地 uploads/（零成本）。

本地模式不需要改前端、不需要重新 build，因为：
  · app/main.py 已把 <backend>/uploads 挂载到 /uploads（StaticFiles）
  · Nginx 已把 /uploads/ 反代到 127.0.0.1:8000
  · 前端 next.config.ts 里已有 /uploads/:path* 的 rewrite
所以直接返回相对路径 /uploads/<文件名> 即可，正文插图和封面图都能显示。

两种模式都会先压缩图片（Pillow 本来就是依赖）：
  · 宽度 > MAX_WIDTH 等比缩小
  · 不透明图 → JPEG（quality 85，progressive）
  · 带透明通道的图 → WebP（保留透明）
  · GIF / SVG 原样保留
  · 压缩后反而比原图大，就保留原图
"""

import logging
import uuid
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from PIL import Image

from app.deps import get_current_user
from app.config import (
    COS_SECRET_ID,
    COS_SECRET_KEY,
    COS_REGION,
    COS_BUCKET,
    COS_CUSTOM_DOMAIN,
    COS_PREFIX,
)

logger = logging.getLogger("kirameku.upload")

router = APIRouter(prefix="/api/upload", tags=["上传"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/svg+xml"}
MAX_SIZE = 10 * 1024 * 1024      # 单文件上限 10MB
MAX_WIDTH = 1600                 # 超过就等比缩小
JPEG_QUALITY = 85
WEBP_QUALITY = 82

# app/api/upload.py → parent=api, parent.parent=app, parent.parent.parent=后端根目录
UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

EXT_BY_TYPE = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
    "image/svg+xml": "svg",
}

_cos_client = None


def cos_enabled() -> bool:
    """只有三个关键项都填了才认为启用了 COS"""
    return bool(COS_SECRET_ID and COS_SECRET_KEY and COS_BUCKET)


def _get_cos_client():
    global _cos_client
    if _cos_client is None:
        from qcloud_cos import CosConfig, CosS3Client  # 延迟导入，本地模式不需要它

        _cos_client = CosS3Client(
            CosConfig(
                Region=COS_REGION,
                SecretId=COS_SECRET_ID,
                SecretKey=COS_SECRET_KEY,
                Scheme="https",
            )
        )
    return _cos_client


def compress_image(content: bytes, content_type: str):
    """压缩图片。返回 (data, ext, content_type)；不是有效图片时返回 (None, None, None)。"""
    # GIF / SVG 不重编码（会破坏动画或矢量）
    if content_type in ("image/gif", "image/svg+xml"):
        return None, None, None

    try:
        img = Image.open(BytesIO(content))
        img.load()
    except Exception:
        return None, None, None

    width, height = img.size
    if width > MAX_WIDTH:
        new_h = max(1, int(height * MAX_WIDTH / width))
        img = img.resize((MAX_WIDTH, new_h), Image.LANCZOS)

    buf = BytesIO()
    try:
        if img.mode in ("P", "RGBA", "LA"):
            # 带透明 → WebP，保留透明通道
            img.save(buf, "WEBP", quality=WEBP_QUALITY, method=6)
            out = buf.getvalue()
            if len(out) < len(content):
                return out, "webp", "image/webp"
        else:
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.save(buf, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
            out = buf.getvalue()
            if len(out) < len(content):
                return out, "jpg", "image/jpeg"
    except Exception as exc:  # noqa: BLE001 —— 压缩只是优化，失败不能影响上传
        logger.warning("图片压缩失败，保留原图: %s", exc)

    return None, None, None


def _save_local(data: bytes, ext: str) -> str:
    filename = f"{uuid.uuid4().hex}.{ext}"
    (UPLOAD_DIR / filename).write_bytes(data)
    return f"/uploads/{filename}"


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    _: dict = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"不支持的文件类型: {file.content_type}")

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(400, "文件大小不能超过 10MB")

    # 方向（前端瀑布流用）
    orientation = "landscape"
    try:
        with Image.open(BytesIO(content)) as im:
            w, h = im.size
            orientation = "landscape" if w >= h else "portrait"
    except Exception:
        pass

    # 压缩（失败则用原图）
    ext = EXT_BY_TYPE.get(file.content_type, "bin")
    data, content_type = content, file.content_type
    compressed, new_ext, new_type = compress_image(content, file.content_type)
    if compressed is not None:
        data, ext, content_type = compressed, new_ext, new_type

    # ① 优先 COS
    if cos_enabled():
        key = f"{COS_PREFIX}{uuid.uuid4().hex}.{ext}"
        try:
            _get_cos_client().put_object(
                Bucket=COS_BUCKET, Key=key, Body=data, ContentType=content_type
            )
            return {
                "url": f"{COS_CUSTOM_DOMAIN.rstrip('/')}/{key}",
                "orientation": orientation,
                "mode": "cos",
                "size": len(data),
            }
        except Exception as exc:  # noqa: BLE001 —— COS 挂了就降级本地，图片不能丢
            logger.warning("上传 COS 失败，降级到本地存储: %s", exc)

    # ② 本地（零成本）
    try:
        url = _save_local(data, ext)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"本地保存失败: {exc}")

    return {
        "url": url,
        "orientation": orientation,
        "mode": "local",
        "size": len(data),
    }


@router.get("/storage")
def storage_info():
    """看看当前用的是哪种存储，以及本地目录占多大"""
    files = list(UPLOAD_DIR.glob("*")) if UPLOAD_DIR.exists() else []
    total = sum(f.stat().st_size for f in files if f.is_file())
    return {
        "mode": "cos" if cos_enabled() else "local",
        "local_dir": str(UPLOAD_DIR),
        "local_files": len(files),
        "local_bytes": total,
        "local_mb": round(total / 1024 / 1024, 2),
        "cos_bucket": COS_BUCKET if cos_enabled() else "",
        "max_width": MAX_WIDTH,
        "note": "mode=local 表示图片存在服务器本地，零成本",
    }
