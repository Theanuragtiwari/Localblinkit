from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from .api.v1.router import router as core_router
from .config import settings
from .db import Base, engine
from .middleware import RateLimitMiddleware, SecurityHeadersMiddleware
from .responses import error

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

origins = [x.strip() for x in settings.CORS_ORIGINS.split(',')] if settings.CORS_ORIGINS != '*' else ['*']
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, limit_per_minute=settings.RATE_LIMIT_PER_MINUTE)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    code_map = {
        401: 'UNAUTHORIZED',
        403: 'FORBIDDEN',
        404: 'NOT_FOUND',
        409: 'CONFLICT',
        422: 'VALIDATION_ERROR',
        429: 'RATE_LIMITED',
        500: 'SERVER_ERROR',
    }
    return error(str(exc.detail), code_map.get(exc.status_code, 'HTTP_ERROR'), exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    return error('Request validation failed', 'VALIDATION_ERROR', 422, {'issues': exc.errors()})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, __: Exception):
    return error('Internal server error', 'SERVER_ERROR', 500)


# v1 routes
app.include_router(core_router, prefix=settings.API_V1_PREFIX)
# backward-compatible routes for existing static frontend
app.include_router(core_router)
