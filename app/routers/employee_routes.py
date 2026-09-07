"""
Employee management routes. All routes require a valid JWT.
Write operations are additionally restricted by role:

    admin    -> create, view, update, delete
    manager  -> create, view, update
    employee -> view only
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import crud, schemas, models
from app.auth import get_current_user, require_roles
from app.database import get_db

router = APIRouter(prefix="/employees", tags=["Employees"])

# Role groups reused across routes for readability.
CAN_CREATE = require_roles(models.RoleEnum.admin, models.RoleEnum.manager)
CAN_UPDATE = require_roles(models.RoleEnum.admin, models.RoleEnum.manager)
CAN_DELETE = require_roles(models.RoleEnum.admin)


def _get_employee_or_404(db: Session, employee_id: int) -> models.Employee:
    db_employee = crud.get_employee(db, employee_id)
    if not db_employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return db_employee


@router.post(
    "",
    response_model=schemas.EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(CAN_CREATE)],
)
def create_employee(
    employee_in: schemas.EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if crud.get_employee_by_email(db, employee_in.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employee email already exists")

    try:
        return crud.create_employee(db, employee_in, created_by=current_user.id)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not create employee")


@router.get("", response_model=schemas.PaginatedEmployeeResponse)
def list_employees(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search by employee name"),
    department: Optional[str] = Query(None, description="Filter by exact department"),
    min_salary: Optional[float] = Query(None, ge=0),
    max_salary: Optional[float] = Query(None, ge=0),
    active_only: bool = Query(True, description="Return only active employees"),
    sort_by: Optional[str] = Query(None, pattern="^(salary|joining_date)$"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if min_salary is not None and max_salary is not None and min_salary > max_salary:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_salary cannot be greater than max_salary",
        )

    return crud.list_employees(
        db,
        page=page,
        limit=limit,
        search=search,
        department=department,
        min_salary=min_salary,
        max_salary=max_salary,
        active_only=active_only,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/{employee_id}", response_model=schemas.EmployeeResponse)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return _get_employee_or_404(db, employee_id)


@router.put(
    "/{employee_id}",
    response_model=schemas.EmployeeResponse,
    dependencies=[Depends(CAN_UPDATE)],
)
def update_employee(
    employee_id: int,
    employee_in: schemas.EmployeeUpdate,
    db: Session = Depends(get_db),
):
    db_employee = _get_employee_or_404(db, employee_id)

    if employee_in.email and employee_in.email != db_employee.email:
        existing = crud.get_employee_by_email(db, employee_in.email)
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employee email already exists")

    try:
        return crud.update_employee(db, db_employee, employee_in)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not update employee")


@router.put(
    "/{employee_id}/transfer",
    response_model=schemas.EmployeeResponse,
    dependencies=[Depends(CAN_UPDATE)],
)
def transfer_employee(
    employee_id: int,
    transfer_in: schemas.EmployeeTransfer,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Step 15: transfers an employee to a new department and writes an
    audit record in a single transaction (both succeed or both roll back).
    """
    db_employee = _get_employee_or_404(db, employee_id)
    return crud.transfer_employee_department(
        db, db_employee, transfer_in.new_department, performed_by=current_user.id
    )


@router.delete(
    "/{employee_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(CAN_DELETE)],
)
def delete_employee(employee_id: int, db: Session = Depends(get_db)):
    """Soft-delete: sets is_active = False instead of removing the row."""
    db_employee = _get_employee_or_404(db, employee_id)
    crud.soft_delete_employee(db, db_employee)
    return {"detail": f"Employee {employee_id} has been deactivated"}
