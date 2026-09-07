"""
Pydantic schemas used for request validation and response serialization.
Keeping these separate from the SQLAlchemy models means the API never
accidentally leaks internal fields like password hashes.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator

from app.models import RoleEnum


# ---------------------------------------------------------------------------
# User / Auth schemas
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: RoleEnum = RoleEnum.employee


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    role: RoleEnum
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str  # user id, as a string, per JWT convention
    username: str
    role: RoleEnum
    exp: int


# ---------------------------------------------------------------------------
# Employee schemas
# ---------------------------------------------------------------------------

class EmployeeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    department: str = Field(min_length=1, max_length=80)
    salary: Decimal = Field(gt=0, description="Must be a positive number")
    joining_date: date

    @field_validator("salary")
    @classmethod
    def salary_must_be_reasonable(cls, v: Decimal) -> Decimal:
        if v > Decimal("100000000"):
            raise ValueError("salary value is unrealistically high")
        return v


class EmployeeUpdate(BaseModel):
    # All fields optional -> supports partial updates.
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    department: Optional[str] = Field(default=None, min_length=1, max_length=80)
    salary: Optional[Decimal] = Field(default=None, gt=0)
    joining_date: Optional[date] = None


class EmployeeTransfer(BaseModel):
    new_department: str = Field(min_length=1, max_length=80)


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    department: str
    salary: Decimal
    joining_date: date
    is_active: bool
    created_by: int
    created_at: datetime
    updated_at: datetime


class PaginatedEmployeeResponse(BaseModel):
    page: int
    limit: int
    total_records: int
    total_pages: int
    data: List[EmployeeResponse]
