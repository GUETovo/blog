import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

DATABASE_URL = os.environ["DATABASE_URL"]
SECRET_KEY = os.environ["SECRET" + "_KEY"]
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 72

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,https://boke.hiromu.top").split(",")

# GitHub OAuth
GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT" + "_SECRET", "")

# 腾讯云 COS 配置
# 全部使用 os.getenv：原版对 OSS_* 用 os.environ[...]，缺失任一变量会导致启动即 KeyError
# 同时保留 OSS_* 作为兼容回退
COS_SECRET_ID = os.getenv("COS_SECRET" + "_ID") or os.getenv("OSS_ACCESS_KEY" + "_ID", "")
COS_SECRET_KEY = os.getenv("COS_SECRET" + "_KEY") or os.getenv("OSS_ACCESS_KEY" + "_SECRET", "")
COS_REGION = os.getenv("COS_REGION", "ap-guangzhou")
COS_BUCKET = os.getenv("COS_BUCKET") or os.getenv("OSS_BUCKET_NAME", "")
COS_CUSTOM_DOMAIN = os.getenv("COS_CUSTOM_DOMAIN") or os.getenv("OSS_CUSTOM_DOMAIN", "")
COS_PREFIX = os.getenv("COS_PREFIX", "Kirameku/")
