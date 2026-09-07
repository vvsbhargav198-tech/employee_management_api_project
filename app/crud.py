"""
Database access layer. All SQLAlchemy query logic lives here, kept
separate from the route handlers in app/routers/.
"""
from math import ceil
from typing import Optional

from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from app import models, schemas


# ---------------------------------------------------------------------------
# User operations
# ---------------------------------------------------------------------------

def get_user_by_username_or_email(db: Session, identifier: str) -> Optional[models.User]:
    stmt = select(models.User).where(
        or_(models.User.username == identifier, models.User.email == identifier)
    )
    return db.execute(stmt).scalars().first()


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    stmt = select(models.User).where(models.User.username == username)
    return db.execute(stmt).scalars().first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    stmt = select(models.User).where(models.User.email == email)
    return db.execute(stmt).scalars().first()


def create_user(db: Session, user_in: schemas.UserCreate, hashed_password: str) -> models.User:
    db_user = models.User(
        username=user_in.username,
        email=user_in.email,
        password=hashed_password,
        role=user_in.role,
        is_active=True,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# ---------------------------------------------------------------------------
# Employee operations
# ---------------------------------------------------------------------------

def get_employee_by_email(db: Session, email: str) -> Optional[models.Employee]:
    stmt = select(models.Employee).where(models.Employee.email == email)
    return db.execute(stmt).scalars().first()


def get_employee(db: Session, employee_id: int) -> Optional[models.Employee]:
    stmt = select(models.Employee).where(models.Employee.id == employee_id)
    return db.execute(stmt).scalars().first()


def create_employee(db: Session, employee_in: schemas.EmployeeCreate, created_by: int) -> models.Employee:
    db_employee = models.Employee(
        name=employee_in.name,
        email=employee_in.email,
        department=employee_in.department,
        salary=employee_in.salary,
        joining_date=employee_in.joining_date,
        created_by=created_by,
        is_active=True,
    )
    db.add(db_employee)
    db.commit()
    db.refresh(db_employee)
    return db_employee


def update_employee(
    db: Session, db_employee: models.Employee, employee_in: schemas.EmployeeUpdate
) -> models.Employee:
    update_data = employee_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_employee, field, value)
    db.commit()
    db.refresh(db_employee)
    return db_employee


def soft_delete_employee(db: Session, db_employee: models.Employee) -> models.Employee:
    db_employee.is_active = False
    db.commit()
    db.refresh(db_employee)
    return db_employee


def transfer_employee_department(
    db: Session,
    db_employee: models.Employee,
    new_department: str,
    performed_by: int,
) -> models.Employee:
    """
    Step 15: transfer an employee to a new department and write an audit
    record, both inside a single transaction. If anything fails, both
    the department change and the audit row are rolled back together.
    """
    old_department = db_employee.department
    try:
        db_employee.department = new_department

        activity = models.EmployeeActivity(
            employee_id=db_employee.id,
            action="DEPARTMENT_TRANSFER",
            details=f"{old_department} -> {new_department}",
            performed_by=performed_by,
        )
        db.add(activity)

        # Single commit -> both the employee update and the audit insert
        # are written atomically. If either add/flush fails, we roll back.
        db.commit()
        db.refresh(db_employee)
        return db_employee
    except Exception:
        db.rollback()
        raise


def list_employees(
    db: Session,
    page: int = 1,
    limit: int = 10,
    search: Optional[str] = None,
    department: Optional[str] = None,
    min_salary: Optional[float] = None,
    max_salary: Optional[float] = None,
    active_only: bool = True,
    sort_by: Optional[str] = None,  # "salary" or "joining_date"
    sort_order: str = "asc",
) -> schemas.PaginatedEmployeeResponse:
    stmt = select(models.Employee)
    count_stmt = select(models.Employee)

    filters = []
    if active_only:
        filters.append(models.Employee.is_active == True)  # noqa: E712
    if search:
        like_pattern = f"%{search}%"
        filters.append(models.Employee.name.ilike(like_pattern))
    if department:
        filters.append(models.Employee.department == department)
    if min_salary is not None:
        filters.append(models.Employee.salary >= min_salary)
    if max_salary is not None:
        filters.append(models.Employee.salary <= max_salary)

    for f in filters:
        stmt = stmt.where(f)
        count_stmt = count_stmt.where(f)

    if sort_by in ("salary", "joining_date"):
        column = getattr(models.Employee, sort_by)
        stmt = stmt.order_by(column.desc() if sort_order == "desc" else column.asc())
    else:
        stmt = stmt.order_by(models.Employee.id.asc())

    total_records = len(db.execute(count_stmt).scalars().all())
    total_pages = max(1, ceil(total_records / limit)) if limit else 1

    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)
    records = db.execute(stmt).scalars().all()

    return schemas.PaginatedEmployeeResponse(
        page=page,
        limit=limit,
        total_records=total_records,
        total_pages=total_pages,
        data=[schemas.EmployeeResponse.model_validate(r) for r in records],
    )
