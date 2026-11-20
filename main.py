from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from os import getenv
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from typing import Annotated

from database import engine, Base, get_db
from models import User
from security import hash_password, verify_password

load_dotenv()

app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    SessionMiddleware,
    secret_key=getenv("SECRET_KEY"),
    max_age=24 * 60 * 60,
    same_site="lax",
    https_only=False
)

Base.metadata.create_all(bind=engine)



@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="home.html"
    )



@app.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="register.html"
    )


@app.post("/register")
def register_user(
    request: Request,
    name: Annotated[str, Form()],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    db = Depends(get_db)
):

    #check password length
    if len(password) < 8:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={"error": "Password must contain at least 8 characters."}
        )

    #checking if email already exits
    existing_user = db.query(User).filter(User.email == email).first()

    if existing_user:
        return templates.TemplateResponse(
            request=request,
            name="register.html", 
            context={"error": "Email is already registered."}
        )

    hashed_password = hash_password(password)

    new_user = User(
        name=name,
        email=email,
        password_hash=hashed_password,
        role="student"
    )

    db.add(new_user)
    db.commit()

    return RedirectResponse(
        "/login",
        status_code=303
    )




@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html"
    )


@app.post("/login")
def login_user(
    request: Request,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    db=Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()


    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Invalid email or password."}
        )

    request.session.clear()
    request.session["user_id"] = user.id

    if user.role == "admin":
        return RedirectResponse("/admin", status_code=303)

    return RedirectResponse(
        "/dashboard",
        status_code=303
    )


@app.get("/dashboard")
def dashboard(request: Request, db=Depends(get_db)):
    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse("/login", status_code=303)

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        request.session.clear()
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"user": user}
    )



@app.get("/logout")
def logout(request: Request):
    request.session.clear()

    return RedirectResponse(
        "/login",
        status_code=303
    )



@app.get("/admin")
def admin_page(request: Request, db=Depends(get_db)):

    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse("/login", status_code=303)

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        request.session.clear()
        return RedirectResponse("/login", status_code=303)

    if user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Access Denied"
        )

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={"user": user}
    )