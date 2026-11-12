import argparse
import sys
from sqlalchemy.orm import Session
from app.database import SessionLocal, init_db
from app.models.user import User, Profile, UserRole
from app.core.security import get_password_hash


def create_admin_user(
    db: Session,
    email: str,
    password: str,
    display_name: str = "Administrador Nexora",
) -> User:
    """
    Internal CLI/administrative helper to provision an administrator account.
    Public registration (/api/v1/auth/register) is strictly restricted to marca/creador.
    """
    if len(password) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres.")

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise ValueError(f"Ya existe un usuario con el correo {email}.")

    admin = User(
        email=email,
        hashed_password=get_password_hash(password),
        role=UserRole.ADMINISTRADOR.value,
        is_active=True,
    )
    db.add(admin)
    db.flush()

    profile = Profile(
        user_id=admin.id,
        display_name=display_name,
        bio="Cuenta administrativa interna de Nexora.",
        location_declared="Colombia",
        niche="Administración",
        average_rating=0.0,
        verified_reviews_count=0,
    )
    db.add(profile)
    db.commit()
    db.refresh(admin)
    return admin


def main() -> int:
    parser = argparse.ArgumentParser(description="CLI administrativo interno de Nexora")
    subparsers = parser.add_subparsers(dest="command", required=True)

    admin_parser = subparsers.add_parser("create-admin", help="Crear una cuenta de administrador")
    admin_parser.add_argument("--email", required=True, help="Correo del administrador")
    admin_parser.add_argument("--password", required=True, help="Contraseña (mínimo 8 caracteres)")
    admin_parser.add_argument("--display-name", default="Administrador Nexora", help="Nombre visible")

    args = parser.parse_args()

    if args.command == "create-admin":
        init_db()
        db = SessionLocal()
        try:
            user = create_admin_user(
                db=db,
                email=args.email,
                password=args.password,
                display_name=args.display_name,
            )
            print(f"Administrador creado exitosamente: id={user.id}, email={user.email}")
            return 0
        except Exception as exc:
            db.rollback()
            print(f"Error al crear administrador: {exc}", file=sys.stderr)
            return 1
        finally:
            db.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

