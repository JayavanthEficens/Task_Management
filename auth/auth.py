from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi.security import HTTPBearer
from fastapi import Depends, HTTPException

oauth2_scheme = HTTPBearer()

SECRET_KEY = "9a6581b8e294705b87edb8faef7d98ee5c65af78ead72c6d59cbfb79868aea8z"
ALG = "HS256"

def create_token(data : dict):
    to_encode = data.copy()
    expire = datetime.now() + timedelta(minutes=15)
    to_encode.update({"exp" : expire})
    encodeed_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALG)
    return encodeed_jwt

def decode_token(token : str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=ALG)
        usermail: str = payload.get("usermail")
        if usermail is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        userrole : str = payload.get("role")
        userid : int = payload.get("id")
        return [userrole, userid]
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")