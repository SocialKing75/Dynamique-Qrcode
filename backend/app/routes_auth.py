from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from . import schemas, models, auth
from .utils import generate_slug
from typing import Optional
import smtplib
from email.message import EmailMessage
import os

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(data: schemas.UserCreate, background_tasks: BackgroundTasks):
    user = await models.User.find_one(models.User.email == data.email)
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed = auth.get_password_hash(data.password)
    user = models.User(email=data.email, hashed_password=hashed, is_active=True, is_verified=False)
    await user.insert()

    # create verification token
    token = auth.create_access_token({"sub": str(user.id), "action": "verify"}, expires_delta=None)
    verify_url = f"/auth/verify?token={token}"

    # send email in background (if SMTP configured)
    def send_email():
        host = os.getenv("SMTP_HOST")
        if not host:
            print("Email verification link:", verify_url)
            return
        try:
            msg = EmailMessage()
            msg.set_content(f"Verify your email: {verify_url}")
            msg["Subject"] = "Verify your account"
            msg["From"] = os.getenv("EMAIL_FROM")
            msg["To"] = user.email
            s = smtplib.SMTP(host, int(os.getenv("SMTP_PORT", 587)))
            s.starttls()
            s.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
            s.send_message(msg)
            s.quit()
        except Exception as e:
            print("Failed to send email:", e)

    background_tasks.add_task(send_email)
    return {"msg": "User created. Verify via email link sent (or check logs)."}


@router.get("/verify")
async def verify(token: Optional[str] = None):
    if not token:
        raise HTTPException(status_code=400, detail="Missing token")
    payload = auth.decode_token(token)
    if not payload or payload.get("action") != "verify":
        raise HTTPException(status_code=400, detail="Invalid token")
    user_id = payload.get("sub")
    user = await models.User.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_verified = True
    await user.save()
    return {"msg": "Email verified."}


@router.post("/login")
async def login(data: schemas.UserCreate):
    user = await models.User.find_one(models.User.email == data.email)
    if not user or not auth.verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not verified")
    access = auth.create_access_token({"sub": str(user.id)})
    refresh = auth.create_refresh_token({"sub": str(user.id)})
    return {"access_token": access, "refresh_token": refresh}


@router.post("/refresh")
async def refresh():
    # Simplified; in production validate token type and expiry
    # TODO: implement refresh token flow (validate refresh token, issue new access token)
    return {"msg": "Not implemented in demo"}
