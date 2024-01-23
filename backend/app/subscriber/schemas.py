from pydantic import BaseModel

class CustomerBase(BaseModel):
    name: str
    phone: int
    phone_prefix: int
    zip_code: str
    number: str
    street: str| None
    city: str| None
    state: str| None
    district: str| None
    complement: str | None
    custom_variables: list | None = []
class CustomerCreate(CustomerBase):
    email: str
    cpf_cnpj: str
    

class Subscription(BaseModel):
    customer: CustomerCreate
    payment_token: str
