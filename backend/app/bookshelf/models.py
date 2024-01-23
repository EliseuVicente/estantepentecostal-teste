from aredis_om import HashModel, Field
from ..dependencies import get_settings
from datetime import datetime
from redis import asyncio as redis


from urllib.parse import urlparse
url = urlparse(get_settings().redis_url)
class Book(HashModel):
    code: str = Field(index=True)
    img: str
    created_at: datetime | None

    class Meta:
        database = redis.Redis(host=url.hostname, port=url.port, username=url.username, password=url.password, ssl=True, ssl_cert_reqs=None)
