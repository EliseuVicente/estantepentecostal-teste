import requests
from .dependencies import get_settings, AppSettings
from fastapi_jwt_auth import AuthJWT
from fastapi import HTTPException

async def iugu_call(url: str, method: str = 'get', params: dict = {}, data: dict = {}, settings: AppSettings = get_settings()):
    r = requests.request(method, f"https://api.iugu.com/v1/{url}", headers={
        'Authorization': f'Basic {settings.iugu_token}'}, params=params, json=data)
    return r.json()

async def omie_call(url: str, call: str = 'get', params: dict = {}, settings: AppSettings = get_settings()):
    pload = {
        "call": call,
        "app_key": settings.omie_key,
        "app_secret": settings.omie_secret,
        "param": [params]
    }
    r = requests.post(
        f"https://app.omie.com.br/api/v1/{url}", json=pload)
    return r

async def check_permission(role, Authorize: AuthJWT):
    print("check")
    Authorize.jwt_required()
    print(Authorize.get_raw_jwt())
    if Authorize.get_raw_jwt()['role'] != 'admin' and Authorize.get_raw_jwt()['role'] !=role :
        raise HTTPException(status_code=401)
