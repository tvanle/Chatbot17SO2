from fastapi import APIRouter, Depends, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from BE.db.session import get_db
from BE.services.authService import AuthService

# Controller: Tầng giao tiếp với FE, xử lý HTTP requests/responses
router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login")
def login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    # để FE dễ xử lý, luôn trả HTTP 200, field ok True/False (đừng 401)
    result = AuthService.checkLogin(db, email, password)
    return JSONResponse(content=result, status_code=200)

@router.post("/register")
def register(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    result = AuthService.register(db, name, email, password)
    return JSONResponse(content=result, status_code=200)

@router.post("/logout")
def logout():
    return JSONResponse(content={"ok": True, "message": "Đăng xuất thành công"}, status_code=200)

@router.get("/profile")
def profile(
    user_id: int,
    db: Session = Depends(get_db),
):
    result = AuthService.getProfile(db, user_id)
    return JSONResponse(content=result, status_code=200)
