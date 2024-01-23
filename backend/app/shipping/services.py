from ..services import omie_call
# from ..dependencies import get_settings
from datetime import datetime,date, timedelta
import json
from pathlib import Path

with open("sents_by_code.json", "r") as read_file:
    legacy = json.load(read_file)


def get_sent_params(client, cod_int, cod_prod, price):
    # settings = get_settings()
    # dev = '2' if 'localhost' in settings.api_url else '3'
    
    cod_int = f"{client}{cod_prod}"
    print('codigo integração', cod_int)

    print("cod_prod", cod_prod)
    params = {
            "cabecalho": {
                "codigo_cliente": client,
                "data_previsao": (date.today() + timedelta(days=5)).strftime(
                    "%d/%m/%Y"
                ),
                "codigo_pedido_integracao": cod_int,
                "etapa": "50",
                "codigo_parcela": "000",
            },
            "det": [
                {
                    "ide": {"codigo_item_integracao": "1"},
                    "produto": {
                        "codigo_produto": cod_prod,
                        "quantidade": 1,
                        "valor_unitario": price,
                    },
                }
            ],
            "informacoes_adicionais": {
                "codigo_categoria": "1.01.03",
                "codigo_conta_corrente": 3700219947,
                "consumidor_final": "S",
                "enviar_email": "S",
                "codVend": 3876023028,
            },
            "frete":{ 
                "codigo_transportadora": 3107974777,
                "modalidade":'0'
            }
        }
    return params

#async def get_client_code(person):
#    params = {
#        "pagina": 1,
 #       "registros_por_pagina": 50,
#        "apenas_importado_api": "N",
#        "clientesFiltro": {
#            "codigo_cliente": person,
#        },
#    }
#    json_params = json.dumps(params)
#    print("Params GERAL/CLIENTES", json_params)
#    response = await omie_call(
#        url="geral/clientes/", call="ListarClientesResumido", params=json_params
#    )
#    if response.status_code != 200:

#        return False
#    return response.json()["clientes_cadastro_resumido"][0]["codigo_cliente"]

async def get_client_code(person):
    params = {
        "pagina": 1,
        "registros_por_pagina": 50,
        "apenas_importado_api": "N",
        "clientesFiltro": {
            "cnpj_cpf": person,
        },
    }
    json_params = json.dumps(params)
    print("Params GERAL/CLIENTES", params)
    response = await omie_call(
        url="geral/clientes/", call="ListarClientesResumido", params=params
    )
    print("Response para validar filtro", response)
    if response.status_code != 200:
        return False
    print("Response.JSON",response.json())
    return response.json()["clientes_cadastro_resumido"][0]["codigo_cliente"]
    #return response.json()

async def get_sents(client):
    params = {
        "registros_por_pagina": 500,
        "apenas_importado_api": "N",
        "filtrar_por_cliente": client,
        "filtrar_por_vendedor": "3876023028",
        "apenas_resumo": "N",
    }
    resp = await omie_call(url="produtos/pedido/", call="ListarPedidos", params=params)
    resp = [] if resp.status_code != 200 else resp.json()["pedido_venda_produto"]
    if str(client) in legacy:
        resp.extend([{"det":[{"produto":{"codigo_produto": c}}], "frete":{"codigo_rastreio":""}} for c in legacy[str(client)]])
    return resp


async def put_omie_client(customer):
    params = {
            "razao_social": customer["name"],
            "nome_fantasia": customer["name"],
            "telefone1_ddd": customer["phone_prefix"],
            "telefone1_numero": customer["phone"],
            "endereco": customer["street"],
            "endereco_numero": customer["number"],
            "bairro": customer["district"],
            "complemento": customer["complement"],
            "estado": customer["state"],
            "cidade": customer["city"],
            "cep": customer["zip_code"],
            "codigo_pais": "BR",
        }

    omie_id = await get_client_code(customer["cpf_cnpj"])
    if not omie_id:
        params["email"] = customer["email"]
        params["cnpj_cpf"] = customer["cpf_cnpj"]
        params["codigo_cliente_integracao"] = customer["cpf_cnpj"]
        resp = await omie_call(url="geral/clientes/", call="IncluirCliente", params=params)
       
    else:
        params["codigo_cliente_omie"] = omie_id
        resp = await omie_call(url="geral/clientes/", call="AlterarCliente", params=params)
    resp = resp.json()
    print("resp", resp)
    return resp["codigo_cliente_omie"]