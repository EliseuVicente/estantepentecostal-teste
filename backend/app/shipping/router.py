from fastapi_jwt_auth import AuthJWT
from fastapi import APIRouter, Depends, Request
from ..services import iugu_call, check_permission, omie_call
from ..bookshelf.models import Book
from .services import get_sents, get_client_code, get_sent_params
import json

router = APIRouter()


@router.post("/")
async def add_shipping( request: Request):
    print("Inicio da API 1")
    form = await request.form()
    print(form)
    print(form['data[id]'])
    if form['data[status]'] != "paid":
        print("Fatura recebida não foi paga")
        return None
    invoice = await iugu_call(url="invoices/" + form['data[id]'])
    print(invoice)
    print("-----------")
    if all(f"Estante Pentecostal" not in i["description"] for i in invoice["items"]):
        print("fatura de outra assinatura")
        return None
    invoices = await iugu_call(
        url="invoices",
        params={"status_filter": "paid", "query": form['data[payer_cpf_cnpj]']},
    )
    count = 1
    for inv in invoices["items"]:
        if inv["id"] != invoice["id"] and any(
            f"Estante Pentecostal" in i["description"] for i in inv["items"]
        ):
            count += 1
    if count == 0:
        print("Cliente sem nenhuma fatura da estante paga")
        return None
    omie_id = await get_client_code(form['data[payer_cpf_cnpj]'])
    print(omie_id)
    if not omie_id:
        print("Cliente não cadastrado no omie")
        return None
    books = [await Book.get(pk) async for pk in await Book.all_pks()]
    books = sorted(books, key=lambda x: x.created_at)
    sents = await get_sents(omie_id)
    books_sent = (
        []
        if len(sents) < 1
        else [sent["det"][0]["produto"]["codigo_produto"] for sent in sents]
    )
    n = (count + 1) // 2
    price = 26.99 if n ==1 else 53.98
    for i in range(n - len(books_sent)):
        temp = next((book.code for book in books if book.code not in books_sent), None)
        if not temp:
            return False
        params = get_sent_params(omie_id, int(str(len(invoices)) + str(i)), temp, price)
        print(params)
        # response = await omie_call(
        #     url="produtos/pedido/", call="IncluirPedido", params=params
        # )
        # print(response.json())
        books_sent.append(temp)
    print("done")
    return {"msg": "Envios verificados com sucesso"}


@router.get("/")
async def get_shipments(Authorize: AuthJWT = Depends()):
    await check_permission("admin", Authorize)
    params = {
        "registros_por_pagina": 500,
        "apenas_importado_api": "N",
        "filtrar_por_vendedor": 3876023028,
        "apenas_resumo": "N",
    }
    resp = await omie_call(url="produtos/pedido/", call="ListarPedidos", params=params)
    return (
        []
        if resp.status_code != 200
        else [
            {
                "id": item["cabecalho"]["numero_pedido"],
                "book_name": item["det"][0]["produto"]["descricao"],
                "date": item["infoCadastro"]["dInc"],
                "status": item["infoCadastro"]["autorizado"],
                "code_shipment": item['frete']['codigo_rastreio']
            }
            for item in resp.json()["pedido_venda_produto"]
        ]
    )

# Esta rota é chamada quando se clicar no botão Verificar Pendências, na página de envio.
@router.post("/refresh", status_code=204)
async def refresh_shipments(Authorize: AuthJWT = Depends()):
    print("Inicio da API 2")
    invoices = await iugu_call(url="invoices", params={"status_filter": "paid"})
    invoices = invoices["items"]
    data = {}
    for invoice in invoices:
        if any(f"Estante Pentecostal" in i["description"] for i in invoice["items"]):
            if invoice["payer_cpf_cnpj"] in data:
                data[invoice["payer_cpf_cnpj"]]["count"] += 1
            else:
                data[invoice["payer_cpf_cnpj"]] = {
                    "id": invoice["account_id"],
                    "count": 1,
                }
    print("data",data)
    for j, person in enumerate(data):
        n = (data[person]["count"] + 1) // 2
        price = 26.99 if n ==1 else 53.98
        print("person INICIAL", person)
        client = await get_client_code(person)
        if not client:
            pass
        books = [await Book.get(pk) async for pk in await Book.all_pks()]
        books = sorted(books, key=lambda x: x.created_at)
        sents = await get_sents(client)
        books_sent = (
            []
            if len(sents) < 1
            else [str(sent["det"][0]["produto"]["codigo_produto"]) for sent in sents]
        )
        
        available_books = [book for book in books if book.code not in books_sent]
        print("available_books", available_books)
        for i in range(n - len(books_sent)):
            temp = next((book.code for book in available_books), None)
            if not temp:
                return False
            if not client:
                return False
            params = get_sent_params(
                client, int(str(len(invoices)) + str(i) + str(j)), temp, price
            )
            print("params", params)
            response = await omie_call(
                url="produtos/pedido/", call="IncluirPedido", params=params
            )
            print("response", response)
            books_sent.append(temp)
    return "ok"
