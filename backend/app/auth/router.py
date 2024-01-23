from fastapi_jwt_auth import AuthJWT
from pydantic import BaseModel
from ..dependencies import get_settings, AppSettings
from fastapi import APIRouter, Depends, Request
from google.oauth2 import id_token
from google.auth.transport import requests
import requests as req
from fastapi.responses import RedirectResponse
from ..services import iugu_call
from urllib.parse import urlparse
from ..shipping.services import get_client_code, put_omie_client

router = APIRouter()


class AuthSettings(BaseModel):
    authjwt_csrf_methods: set = {"GET", "POST", "PUT", "PATCH", "DELETE"}
    authjwt_secret_key: str = get_settings().secret_key
    authjwt_token_location: set = {"cookies"}
    authjwt_cookie_secure: bool = (
        False if "localhost" in get_settings().ui_url else True
    )
    authjwt_cookie_csrf_protect: bool = True
    authjwt_cookie_samesite: str = "lax"
    authjwt_access_token_expires = 43200
    authjwt_cookie_domain: str | None = (
        None
        if "localhost" in get_settings().ui_url
        else "estante-pentecostal.eetad.com"
    )


@AuthJWT.load_config
def get_config():
    return AuthSettings()


@router.get("/token", response_class=RedirectResponse)
async def auth_google(
    code: str,
    request: Request,
    Authorize: AuthJWT = Depends(),
    settings: AppSettings = Depends(get_settings),
):
    # Trocar o código de autorização por um token de acesso usando a API OAuth2 do Google
    url = "https://accounts.google.com/o/oauth2/token"
    params = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_secret_key,
        "redirect_uri": request.url._url.split("?")[0],
    }
    r = req.post(url, params=params).json()
    
    # Verificar o token de acesso usando a biblioteca google.oauth2.id_token
    idinfo = id_token.verify_oauth2_token(
        r["id_token"],
        requests.Request(),
        settings.google_client_id,
        clock_skew_in_seconds=10,
    )
    print("idinfo",idinfo)
    userid = idinfo["email"]
    if userid == settings.admin_email:
        role = "admin"
    else:
        data = await iugu_call(url="customers")
        print("data",data)
        user = (
            next((item for item in data["items"] if item["email"] == userid), None)
            if "items" in data
            else None
        )
        role = "subscriber" if user else None
        if user:
            omie = await get_client_code(user["cpf_cnpj"])
            if not omie:
                a = await put_omie_client(user)
    print("role",role)            
    access_token = Authorize.create_access_token(
        subject=userid,
        user_claims={
            "role": role,
            "cpf": user["cpf_cnpj"] if role == "subscriber" else "",
            "iugu_id": user["id"] if role == "subscriber" else "",
        },
    )

    response = RedirectResponse(settings.ui_url)
    Authorize.set_access_cookies(access_token, response=response)
    return response


@router.get("/user")
async def get_user(
    Authorize: AuthJWT = Depends(), settings: AppSettings = Depends(get_settings)
):
    Authorize.jwt_required()
    return {
        "email": Authorize.get_jwt_subject(),
        "role": Authorize.get_raw_jwt()["role"],
    }


@router.get("/logout")
def logout(Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    Authorize.unset_jwt_cookies()
    return {"msg": "Successfully logout"}
