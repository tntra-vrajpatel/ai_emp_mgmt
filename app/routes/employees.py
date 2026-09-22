from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.employee import get_db
from app.schemas.employee import EmployeeResponse
from app.services.employee_service import get_all_employees

router = APIRouter()


@router.get("/employees", response_model=list[EmployeeResponse])
def list_employees(db: Session = Depends(get_db)):
    return get_all_employees(db)
