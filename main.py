from fastapi import FastAPI, Request, Form, Depends
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from os import getenv
from fastapi.responses import RedirectResponse
from typing import Annotated

from database import engine, Base
from models import User

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

