from pydantic import BaseModel, EmailStr


class ClientCreate(BaseModel):
    name : str
    email: EmailStr
    name_contact: str
    siret: str
    address: str
    zip_code: str
    city:str
    legal_form: str
    vat_number:str | None
    is_professional:bool
    pdp_routing_id:str|None

class ClientUpdate(BaseModel):
    id: int
    name : str | None
    email: EmailStr | None
    name_contact: str | None
    siret: str | None
    address: str | None
    legal_form: str | None
    company_id: int | None

class ClientResponse(BaseModel):
    id: int
    name : str
    email: EmailStr
    name_contact: str
    siret: str
    address: str
    zip_code: str
    city:str
    vat_number:str
    legal_form: str
    company_id: int
    is_professional:bool
    pdp_routing_id:str

    model_config = {"from_attributes": True}
