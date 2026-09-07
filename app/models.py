"""
SQLAlchemy ORM models.

Tables:
  - users:            application accounts used to log in and call the API
  - employees:         employee records managed through the API
  - employee_activity: audit trail rows, e.g. department transfers (Step 15)
"""
import enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Numeric,
    Date,
    ForeignKey,
    Enum,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class RoleEnum(str, enum.Enum):
    admin = "admin"
    manager = "manager"
    employee = "employee"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)  # stores the HASHED password only
    role = Column(Enum(RoleEnum), nullable=False, default=RoleEnum.employee)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Employees this user created (created_by foreign key on employees table)
    employees_created = relationship(
        "Employee",
        back_populates="creator",
        foreign_keys="Employee.created_by",
    )


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    department = Column(String(80), nullable=False, index=True)
    salary = Column(Numeric(10, 2), nullable=False, default=0)
    joining_date = Column(Date, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    creator = relationship("User", back_populates="employees_created", foreign_keys=[created_by])
    activity_logs = relationship("EmployeeActivity", back_populates="employee")


class EmployeeActivity(Base):
    """
    Audit trail row created inside the same transaction as certain
    employee updates (e.g. department transfer). See Step 15.
    """
    __tablename__ = "employee_activity"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    action = Column(String(50), nullable=False)          # e.g. "DEPARTMENT_TRANSFER"
    details = Column(String(255), nullable=True)          # e.g. "IT -> Finance"
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee", back_populates="activity_logs")
