from fastapi_jwt_auth import AuthJWT
from fastapi import APIRouter, Depends, HTTPException, Request
import datetime
from ..services import iugu_call, check_permission, omie_call
from .schemas import *
from ..shipping.services import get_sents, get_client_code, put_omie_client
from ..bookshelf.models import Book


router = APIRouter()


@router.get("/")
async def get_subscribers(request:Request, Authorize: AuthJWT = Depends()):
    print("request", request.__dict__)
    print("inicio")
    await check_permission("subscriber", Authorize)
    print("teste")
    return await iugu_call(url="customers/" + Authorize.get_raw_jwt()["iugu_id"])

@router.get("/customers")
async def get_subscribers(request:Request, Authorize: AuthJWT = Depends()):
    print("request", request.__dict__)
    return await iugu_call(url="customers/")

@router.delete("/subscription/{id}")
async def delete_subscriber(id: str, Authorize: AuthJWT = Depends()):
    await check_permission("subscriber", Authorize)
    resp = await iugu_call(url="subscriptions/" + id, method="delete")
    return resp


@router.put("/subscription")
async def put_subscriber(Authorize: AuthJWT = Depends()):
    await check_permission("subscriber", Authorize)
    subscription = await iugu_call(
        "subscriptions",
        method="post",
        data={
            "customer_id": Authorize.get_raw_jwt()["iugu_id"],
            "plan_identifier": f"estante_pentecostal_{datetime.date.today().year}",
        },
    )
    print(subscription)
    a = await iugu_call(
        f"customers/" + Authorize.get_raw_jwt()["iugu_id"],
        data={"custom_variables": [{"name": "Estante Pentecostal", "value": "S"}]},
        method="put",
    )
    return subscription["id"]


@router.get("/subscription")
async def get_subscriber(Authorize: AuthJWT = Depends()):
    await check_permission("subscriber", Authorize)

    resp = await iugu_call(
        url="subscriptions",
        params={
            "customer_id": Authorize.get_raw_jwt()["iugu_id"],
            "status_filter": "active",
        },
    )
    print("----------------------------------------")
    print(resp)
    print("----------------------------------------")
    subscription = next(
        (s for s in resp["items"] if "Estante Pentecostal" in s["plan_name"]), None
    ) if "items" in resp else None
    return subscription["id"] if subscription else None


@router.get("/payment_methods")
async def get_subscriber_payment_methods(Authorize: AuthJWT = Depends()):
    await check_permission("subscriber", Authorize)
    user = await iugu_call(url="customers/" + Authorize.get_raw_jwt()["iugu_id"])
    response = await iugu_call(
        f'customers/{Authorize.get_raw_jwt()["iugu_id"]}/payment_methods'
    )
    return [
        {**item, "default": item["id"] == user["default_payment_method_id"]}
        for item in response
    ]


@router.post("/payment_methods/{payment_token}")
async def add_subscriber_payment_methods(
    payment_token: str, Authorize: AuthJWT = Depends()
):
    await check_permission("subscriber", Authorize)
    payment = await iugu_call(
        f"customers/" + Authorize.get_raw_jwt()["iugu_id"] + "/payment_methods",
        data={
            "description": "credtcard",
            "token": payment_token,
            "set_as_default": True,
        },
        method="post",
    )
    return payment


@router.put("/default_payment_methods/{payment_id}")
async def change_default_payment_method(
    payment_id: str, Authorize: AuthJWT = Depends()
):
    await check_permission("subscriber", Authorize)
    user = await iugu_call(url="customers/" + Authorize.get_raw_jwt()["iugu_id"])
    user["default_payment_method_id"] = payment_id
    new_user = await iugu_call(
        f"customers/" + Authorize.get_raw_jwt()["iugu_id"], data=user, method="put"
    )
    return new_user


@router.put("/")
async def update_subscriber(customer: CustomerBase, Authorize: AuthJWT = Depends()):
    await check_permission("subscriber", Authorize)
    print(Authorize.get_raw_jwt())
    print(customer)
    new_user = await iugu_call(
        f"customers/" + Authorize.get_raw_jwt()["iugu_id"],
        data=customer.__dict__,
        method="put",
    )
    await put_omie_client(new_user)
    return new_user


@router.delete("/payment_methods/{payment_id}")
async def remove_subscriber_payment_methods(
    payment_id: str, Authorize: AuthJWT = Depends()
):
    await check_permission("subscriber", Authorize)
    payment = await iugu_call(
        f"customers/"
        + Authorize.get_raw_jwt()["iugu_id"]
        + "/payment_methods/"
        + payment_id,
        method="delete",
    )
    return payment


@router.get("/invoices/{invoice_id}")
async def get_invoice(invoice_id:str, Authorize: AuthJWT = Depends()):
    await check_permission("subscriber", Authorize)
    response = await iugu_call(
        "invoices/"+invoice_id
    )
    return response

@router.get("/invoices")
async def get_subscriber_invoices(Authorize: AuthJWT = Depends()):
    await check_permission("subscriber", Authorize)
    response = await iugu_call(
        "invoices", params={"customer_id": Authorize.get_raw_jwt()["iugu_id"]}
    )
    return [
        {k: invoice[k] for k in ("due_date", "status", "secure_url", "id")}
        for invoice in response["items"]
        if any(f"Estante Pentecostal" in i["description"] for i in invoice["items"])
    ]


@router.post("/", status_code=204)
async def add_customer(subscription: Subscription, request:Request, Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    omie_user = await put_omie_client(subscription.customer.__dict__)
    if not omie_user:
        raise HTTPException(status_code=404)
    customer_data = subscription.customer.__dict__
    customer_data["custom_variables"] = [{"name": "estante", "value": "S"}]
    customer_response = await iugu_call("customers", data=customer_data, method="post")
    customer_id = customer_response["id"]
    a = await iugu_call(
        f"customers/{customer_id}/payment_methods",
        data={"description": "credtcard", "token": subscription.payment_token},
        method="post",
    )
    print(a)
    s = await iugu_call(
        "subscriptions",
        method="post",
        data={
            "customer_id": customer_id,
            "plan_identifier": f"estante_pentecostal_{datetime.date.today().year}",
        },
    )
    print(s)
    Authorize.unset_jwt_cookies()
    access_token = Authorize.create_access_token(
        subject=Authorize.get_jwt_subject(),
        user_claims={
            "role": "subscriber",
            "iugu_id": customer_response["id"],
            "cpf": subscription.customer.cpf_cnpj,
        },
    )
    Authorize.set_access_cookies(access_token)
    return


@router.get("/books")
async def get_bookshelf_books(Authorize: AuthJWT = Depends()):
    await check_permission("subscriber", Authorize)
    books = [await Book.get(pk) async for pk in await Book.all_pks()]
    books = sorted(books, key=lambda x: x.created_at)
    params = {
        "registros_por_pagina": 500,
        "filtrar_apenas_omiepdv": "N",
        "apenas_importado_api": "N",
        "produtosPorCodigo": [{"codigo_produto": book.code} for book in books],
    }
    books_omie = await omie_call(
        url="geral/produtos/", call="ListarProdutosResumido", params=params
    )
    books_bookshelf = [
        {
            "img": book.img,
            "name": next(
                x["descricao"]
                for x in books_omie.json()["produto_servico_resumido"]
                if str(x["codigo_produto"]) == book.code
            ),
            "code": book.code,
        }
        for book in books
    ]
    sents = await get_sents(await get_client_code(Authorize.get_raw_jwt()["cpf"]))
    temp = {}
    for sent in sents:
        id=str(sent["det"][0]["produto"]["codigo_produto"])
        temp[id] = {"code": sent["frete"]["codigo_rastreio"]}
    for book in books_bookshelf:
        id = str(book["code"])
        if id in temp:
            book["sent"] = True
            book["shipment_code"] = temp[id]['code']
        else:
            book["sent"] = False
    return books_bookshelf
