from fastapi import FastAPI, Request, status
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError

from app.database import Base, engine
from app.routers import auth_routes, employee_routes


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Employee Management API",
    description="Advanced Employee Management API using FastAPI, JWT, SQLAlchemy, and MySQL",
    version="1.0.0",
)

app.include_router(auth_routes.router)
app.include_router(employee_routes.router)


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "Employee Management API is running"}




@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error", "errors": exc.errors()},
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Database integrity error: a related record may already exist or be missing."},
    )


@app.exception_handler(OperationalError)
async def operational_error_handler(request: Request, exc: OperationalError):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Database is currently unavailable. Please try again shortly."},
    )


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
   
    return await http_exception_handler(request, exc)
