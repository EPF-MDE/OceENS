from dotenv import load_dotenv

load_dotenv()

import uuid
import requests
import msal
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, Response
import os

router = APIRouter()

CLIENT_ID = os.environ.get("ENTRA_CLIENT_ID")
CLIENT_SECRET = os.environ.get("ENTRA_CLIENT_SECRET")
TENANT_ID = os.environ.get("ENTRA_TENANT_ID")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
REDIRECT_URI = os.environ.get("REDIRECT_URI", "http://localhost:8000/auth/callback")
SCOPES = ["User.Read"]


def _build_msal_app():
    return msal.ConfidentialClientApplication(
        CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET
    )


@router.get("/login")
async def login(request: Request):
    state = str(uuid.uuid4())
    request.session["auth_state"] = state
    auth_url = _build_msal_app().get_authorization_request_url(
        scopes=SCOPES, state=state, redirect_uri=REDIRECT_URI
    )
    return RedirectResponse(auth_url)


@router.get("/auth/callback")
async def auth_callback(request: Request):
    from database import get_role

    if request.query_params.get("state") != request.session.get("auth_state"):
        return Response("State invalide", status_code=400)

    token_result = _build_msal_app().acquire_token_by_authorization_code(
        code=request.query_params["code"],
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    graph = requests.get(
        "https://graph.microsoft.com/v1.0/me",
        headers={"Authorization": f"Bearer {token_result['access_token']}"},
    ).json()

    email = graph.get("mail") or graph.get("userPrincipalName")
    role = get_role(email)

    request.session["user"] = {
        "name": graph.get("displayName"),
        "email": email,
        "role": role,
    }

    return RedirectResponse(url=f"/dashboard/{role}")


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(
        f"{AUTHORITY}/oauth2/v2.0/logout?post_logout_redirect_uri=http://localhost:8000"
    )
