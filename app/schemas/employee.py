from typing import Optional

from pydantic import BaseModel, ConfigDict


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    department: Optional[str]
    email: Optional[str]
    name: Optional[str]
    salary: Optional[float]
