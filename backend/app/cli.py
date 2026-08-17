import argparse, getpass
from app.db.session import SessionLocal
from app.models.entities import User
from app.services.auth import hash_password, normalize_email

def create_admin():
    try: email = normalize_email(input("Admin email: "))
    except ValueError as exc: print(str(exc)); print("Admin was not created."); return 1
    password = getpass.getpass("Admin password: ")
    if len(password) < 12: print("Password must contain at least 12 characters."); print("Admin was not created."); return 1
    db = SessionLocal()
    try:
        if db.query(User).filter_by(email=email).first():
            print("Admin email already exists; no changes made."); return 2
        db.add(User(email=email, password_hash=hash_password(password), role="ADMIN", status="ACTIVE")); db.commit(); print("Admin created."); return 0
    finally: db.close()
if __name__ == "__main__":
    argparse.ArgumentParser().parse_args(); raise SystemExit(create_admin())
