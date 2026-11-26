
from fastapi import FastAPI, Request, Form, Depends, HTTPException, UploadFile, File
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from os import getenv
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from typing import Annotated
import os
import uuid


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


# Home page
@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="home.html"
    )


# Registration page
@app.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="register.html"
    )


# Register student
@app.post("/register")
def register_user(
    request: Request,
    name: Annotated[str, Form()],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    phone: Annotated[str, Form()],
    course: Annotated[str, Form()],
    db=Depends(get_db)
):

    if len(password) < 8:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={
                "error": "Password must contain at least 8 characters."
            }
        )

    existing_user = db.query(User).filter(
        User.email == email
    ).first()

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
        role="student",
        phone=phone,
        course=course
    )

    db.add(new_user)
    db.commit()

    return RedirectResponse(
        url="/login",
        status_code=303
    )


# Login page
@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html"
    )


# Login user
@app.post("/login")
def login_user(
    request: Request,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    db=Depends(get_db)
):

    user = db.query(User).filter(
        User.email == email
    ).first()

    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Invalid email or password."}
        )

    request.session.clear()
    request.session["user_id"] = user.id

    if user.role == "admin":
        return RedirectResponse(
            url="/admin",
            status_code=303
        )

    return RedirectResponse(
        url="/dashboard",
        status_code=303
    )


# Student dashboard
@app.get("/dashboard")
def dashboard(request: Request, db=Depends(get_db)):

    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse("/login", status_code=303)

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        request.session.clear()
        return RedirectResponse("/login", status_code=303)

    if user.role != "student":
        raise HTTPException(
            status_code=403,
            detail="Access Denied"
        )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"user": user}
    )


# Edit profile page
@app.get("/edit-profile")
def edit_profile_page(request: Request, db=Depends(get_db)):

    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse("/login", status_code=303)

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        request.session.clear()
        return RedirectResponse("/login", status_code=303)

    if user.role != "student":
        raise HTTPException(
            status_code=403,
            detail="Access Denied"
        )

    return templates.TemplateResponse(
        request=request,
        name="edit_profile.html",
        context={"user": user}
    )




@app.post("/edit-profile")
def update_profile(
    request: Request,
    name: Annotated[str, Form()],
    phone: Annotated[str, Form()],
    course: Annotated[str, Form()],
    profile_image: UploadFile | None = File(default=None),
    db=Depends(get_db)
):
    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse("/login", status_code=303)

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        request.session.clear()
        return RedirectResponse("/login", status_code=303)

    if user.role != "student":
        raise HTTPException(status_code=403, detail="Access Denied")

    user.name = name
    user.phone = phone
    user.course = course

    if profile_image and profile_image.filename:

        allowed_types = ["image/jpeg", "image/png", "image/webp"]

        if profile_image.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail="Only JPG, PNG and WEBP images are allowed."
            )

        image_data = profile_image.file.read()

        if len(image_data) > 2 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="Image size must be less than 2 MB."
            )

        extension = profile_image.filename.rsplit(".", 1)[-1].lower()

        filename = f"{uuid.uuid4()}.{extension}"
        image_path = os.path.join("static", "uploads", filename)

        with open(image_path, "wb") as image_file:
            image_file.write(image_data)

        user.profile_image = f"/static/uploads/{filename}"

    db.commit()

    return RedirectResponse(url="/dashboard", status_code=303)




# Logout
@app.get("/logout")
def logout(request: Request):

    request.session.clear()

    return RedirectResponse(
        url="/login",
        status_code=303
    )


# Admin page
@app.get("/admin")
def admin_page(request: Request, db=Depends(get_db)):

    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse("/login", status_code=303)

    user = db.query(User).filter(
        User.id == user_id
    ).first()

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
