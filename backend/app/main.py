from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi_jwt_auth.exceptions import AuthJWTException
from fastapi.middleware.cors import CORSMiddleware
from .auth.router import router as auth_router
from .subscriber.router import router as subscription_router
from .bookshelf.router import router as bookshelf_router
from .shipping.router import router as shipping_router
from .dependencies import get_settings
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
import aioredis
from redis_om import get_redis_connection
from .bookshelf.models import Book
import logging

logging.basicConfig(level=logging.DEBUG)

from .services import iugu_call
app = FastAPI(title="Estante Pentecostal")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(
    auth_router,
    prefix="/auth",
    tags=["Auth"],
)
app.include_router(
    subscription_router,
    prefix="/subscribers",
    tags=["Subscribers"],
)

app.include_router(
    bookshelf_router,
    prefix="/bookshelf",
    tags=["Bookshelf"],
)
app.include_router(
    shipping_router,
    prefix="/shipping",
    tags=["Shipping"],
)


@app.exception_handler(AuthJWTException)
def authjwt_exception_handler(request: Request, exc: AuthJWTException):
    logging.error(f"Erro na rota {request.url}: {exc}")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.get("/")
async def root():
    logging.debug("Acessando a rota root")
    return {"msg": "Rota Root"}


@app.on_event("startup")
async def startup():
    logging.info("Iniciando a aplicação")
    r = aioredis.from_url(
        get_settings().redis_url, encoding="utf8", decode_responses=True
    )
    FastAPICache.init(RedisBackend(r), prefix="fastapi-cache")