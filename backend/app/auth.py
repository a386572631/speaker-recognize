from fastapi import Header, HTTPException

from .config import get_settings


async def verify_auth(authorization: str = Header(None)) -> str:
    settings = get_settings()
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.split(" ")[1]
    if token != settings.api_key:
        raise HTTPException(status_code=401, detail="Api Key Error")
    return token
