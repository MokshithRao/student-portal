
from fastapi import FastAPI, Request, Form, Depends, HTTPException, UploadFile, File
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from os import getenv
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from typing import Annotated
from sqlalchemy import func, or_
from urllib.parse import urlencode
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

    email = email.strip().lower()

    if len(password) < 8:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={
                "error": "Password must contain at least 8 characters."
            }
        )

    existing_user = db.query(User).filter(
        func.lower(User.email) == email
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

    previous_image_path = user.profile_image
    new_image_path = None

    if profile_image and profile_image.filename:

        allowed_types = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/webp": "webp"
        }
        extension = allowed_types.get(profile_image.content_type)

        if not extension:
            raise HTTPException(
                status_code=400,
                detail="Only JPG, PNG and WEBP images are allowed."
            )

        max_image_size = 2 * 1024 * 1024
        image_data = profile_image.file.read(max_image_size + 1)

        if len(image_data) > max_image_size:
            raise HTTPException(
                status_code=400,
                detail="Image size must be less than 2 MB."
            )

        filename = f"{uuid.uuid4()}.{extension}"
        image_path = os.path.join("static", "uploads", filename)

        with open(image_path, "wb") as image_file:
            image_file.write(image_data)

        new_image_path = f"/static/uploads/{filename}"
        user.profile_image = new_image_path

    user.name = name
    user.phone = phone
    user.course = course

    db.commit()

    if new_image_path:
        remove_profile_image(db, previous_image_path)

    return RedirectResponse(url="/dashboard", status_code=303)




# Logout
@app.get("/logout")
def logout(request: Request):

    request.session.clear()

    return RedirectResponse(
        url="/login",
        status_code=303
    )


def remove_profile_image(db, image_url):
    prefix = "/static/uploads/"

    if not image_url or not image_url.startswith(prefix):
        return

    filename = image_url[len(prefix):]

    if not filename or os.path.basename(filename) != filename:
        return

    image_in_use = db.query(User.id).filter(
        User.profile_image == image_url
    ).first()

    if image_in_use:
        return

    upload_directory = os.path.realpath(os.path.join("static", "uploads"))
    image_path = os.path.join(upload_directory, filename)

    if os.path.islink(image_path):
        return

    real_image_path = os.path.realpath(image_path)
    if os.path.commonpath((upload_directory, real_image_path)) != upload_directory:
        return

    if os.path.isfile(image_path):
        os.remove(image_path)


@app.get("/admin")
def admin_page(request: Request, q: str = "", db=Depends(get_db)):

    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse("/login", status_code=303)

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        request.session.clear()
        return RedirectResponse("/login", status_code=303)

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Access Denied")

    total_students = db.query(User).filter(
        User.role == "student"
    ).count()

    search_query = q.strip()
    student_query = db.query(User).filter(
        User.role == "student"
    )

    if search_query:
        search_pattern = f"%{search_query}%"
        student_query = student_query.filter(
            or_(
                User.name.ilike(search_pattern),
                User.email.ilike(search_pattern)
            )
        )

    students = student_query.order_by(User.id).all()

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "user": user,
            "total_students": total_students,
            "students": students,
            "search_query": search_query,
            "message": request.session.pop("admin_message", None),
            "message_type": request.session.pop("admin_message_type", None)
        }
    )


@app.post("/admin/students/{student_id}/delete")
def delete_student(
    student_id: int,
    request: Request,
    q: str = "",
    db=Depends(get_db)
):
    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse("/login", status_code=303)

    admin = db.query(User).filter(User.id == user_id).first()

    if not admin:
        request.session.clear()
        return RedirectResponse("/login", status_code=303)

    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Access Denied")

    message_type = "error"

    if student_id == admin.id:
        message = "You cannot delete your own account."
    else:
        student = db.query(User).filter(User.id == student_id).first()

        if not student:
            message = "Student not found."
        elif student.role != "student":
            message = "Only student accounts can be deleted."
        else:
            profile_image = student.profile_image
            db.delete(student)
            db.commit()
            remove_profile_image(db, profile_image)
            message = "Student deleted successfully."
            message_type = "success"

    request.session["admin_message"] = message
    request.session["admin_message_type"] = message_type

    search_query = q.strip()
    redirect_url = f"/admin?{urlencode({'q': search_query})}" if search_query else "/admin"

    return RedirectResponse(redirect_url, status_code=303)
