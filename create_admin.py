
from getpass import getpass

from database import SessionLocal
from models import User
from security import hash_password

db = SessionLocal()

name = input("Enter admin name: ")
email = input("Enter admin email: ")
phone = input("Enter admin phone: ")
course = input("Enter department: ")
password = getpass("Enter admin password: ")

existing_admin = db.query(User).filter(User.email == email).first()

if existing_admin:
    print("An account with this email already exists.")
else:
    admin = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role="admin",
        phone=phone,
        course=course
    )

    db.add(admin)
    db.commit()

    print("Admin account created successfully!")

db.close()
