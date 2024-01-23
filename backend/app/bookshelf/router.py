from fastapi_jwt_auth import AuthJWT
from fastapi import APIRouter, Depends, HTTPException
from ..shipping.services import get_sents, get_client_code,put_omie_client
from .models import Book
from ..services import check_permission, iugu_call, omie_call, iugu_call
from datetime import datetime
from ..subscriber.schemas import CustomerBase
router = APIRouter()


@router.get("/chart")
async def get_chart(Authorize: AuthJWT = Depends()):
    invoices = await iugu_call(url="invoices", params={"status_filter": "paid"})
    invoices = invoices["items"] if "items" in invoices else []
    data = {}
    for invoice in invoices:
        if any(f"Estante Pentecostal" in i["description"] for i in invoice["items"]):
            if invoice["payer_cpf_cnpj"] in data:
                data[invoice["payer_cpf_cnpj"]]["count"] += 1
                data[invoice["payer_cpf_cnpj"]]["date"] = invoice["due_date"]
            else:
                data[invoice["payer_cpf_cnpj"]] = {
                    "count": 1,
                }
    return data


@router.post("/", status_code=201)
async def add_book(book: Book, Authorize: AuthJWT = Depends()):
    await check_permission("admin", Authorize)
    book.created_at = datetime.now()
    return await book.save()


@router.get("/stock")
async def get_omie_books(Authorize: AuthJWT = Depends()):
    await check_permission("admin", Authorize)
    params = {"registros_por_pagina": 500, "filtrar_apenas_familia": "3110322093"}
    books = await omie_call(
        url="geral/produtos/", call="ListarProdutosResumido", params=params
    )
    return [
        {"name": book["descricao"], "code": book["codigo_produto"]}
        for book in books.json()["produto_servico_resumido"]
    ]


@router.get("/")
async def get_bookshelf_books(Authorize: AuthJWT = Depends()):
    await check_permission("admin", Authorize)
    books = [await Book.get(pk) async for pk in await Book.all_pks()]
    books = sorted(books, key=lambda x: x.created_at)
    params = {
        "registros_por_pagina": 500,
        "filtrar_apenas_omiepdv": "N",
        "apenas_importado_api": "N",
        "produtosPorCodigo": [{"codigo_produto": book.code} for book in books],
    }
    print("PARAMS", params)
    books_omie = await omie_call(
        url="geral/produtos/", call="ListarProdutosResumido", params=params
    )
    return [
        {
            "pk": book.pk,
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


@router.patch("/", status_code=204)
async def change_image(book_edited: Book, Authorize: AuthJWT = Depends()):
    await check_permission("admin", Authorize)
    book_db = await Book.get(book_edited.pk)
    if not book_db:
        raise HTTPException(status_code=404, detail="ID not found")
    book_db.img = book_edited.img
    return await book_db.save()


@router.delete("/{book_id}", status_code=204)
async def remove_book(book_id: str, Authorize: AuthJWT = Depends()):
    await check_permission("admin", Authorize)
    return await Book.delete(book_id)


@router.get("/subscribes")
async def get_iugu_subscribes(Authorize: AuthJWT = Depends()):
    #await check_permission("admin", Authorize)
    subscribes = await iugu_call(url="customers", params={"query": "estante"})
    return subscribes["items"]


@router.get("/subscribes/{cpf}")
async def get_iugu_subscribes(cpf: str, Authorize: AuthJWT = Depends()):
    #await check_permission("admin", Authorize)
    invoices = await iugu_call(url="invoices", params={"query": cpf})
    data = []
    for invoice in invoices["items"]:
        if any(f"Estante Pentecostal" in i["description"] for i in invoice["items"]):
            data.append(invoice)
    sents = await get_sents(await get_client_code(cpf))
    return {"sents": sents, "invoices": data}


@router.get("/books/{cpf}")
async def get_bookshelf_books(cpf: str, Authorize: AuthJWT = Depends()):
    await check_permission("admin", Authorize)
    sents = await get_sents(await get_client_code(cpf))
    return [
        {
            "id": item["cabecalho"]["numero_pedido"],
            "book_name": item["det"][0]["produto"]["descricao"],
            "date": item["infoCadastro"]["dInc"],
            "status": item["infoCadastro"]["autorizado"],
            "code_shipment": item["frete"]["codigo_rastreio"],
        }
        for item in sents
    ]
@router.put("/subscribers/{cpf}")
async def update_subscriber(cpf:str, customer: CustomerBase, Authorize: AuthJWT = Depends()):
    await check_permission("admin", Authorize)
    new_user = await iugu_call(
        f"customers/" + cpf,
        data=customer.__dict__,
        method="put",
    )
    await put_omie_client(new_user)
    return new_user