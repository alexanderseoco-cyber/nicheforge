import argparse, getpass
from app.db.session import SessionLocal
from app.models.entities import User
from app.services.auth import hash_password, normalize_email

def create_admin():
    email = normalize_email(input("Admin email: "))
    password = getpass.getpass("Admin password: ")
    db = SessionLocal()
    try:
        if db.query(User).filter_by(email=email).first():
            print("Admin email already exists; no changes made."); return 2
        db.add(User(email=email, password_hash=hash_password(password), role="ADMIN", status="ACTIVE")); db.commit(); print("Admin created."); return 0
    finally: db.close()
if __name__ == "__main__":
    argparse.ArgumentParser().parse_args(); raise SystemExit(create_admin())
