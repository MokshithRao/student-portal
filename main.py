from fastapi import FastAPI, Request, Form, Depends
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from os import getenv
from fastapi.responses import RedirectResponse
from typing import Annotated

from database import engine, Base, get_db
from models import User
from security import hash_password

load_dotenv()

app = FastAPI()

templates = Jinja2Templates(directory="templates")

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

