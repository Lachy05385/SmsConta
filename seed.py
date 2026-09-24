# seed.py
import os
from app.auth import get_password_hash
from app.database import SessionLocal
from app import models


def seed_inicial():
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    empresa_nit = os.getenv("EMPRESA_NIT", "900000001")

    if not admin_email or not admin_password:
        raise ValueError("Faltan ADMIN_EMAIL y ADMIN_PASSWORD en el entorno")

    db = SessionLocal()
    try:
        # 1. Empresa
        empresa = db.query(models.Empresa).filter(
            models.Empresa.nit == empresa_nit
        ).first()
        if not empresa:
            empresa = models.Empresa(
                nombre=os.getenv("EMPRESA_NOMBRE", "Empresa Principal ContaFlow"),
                nit=empresa_nit,
                direccion=os.getenv("EMPRESA_DIRECCION", ""),
                telefono=os.getenv("EMPRESA_TELEFONO", ""),
            )
            db.add(empresa)
            db.commit()
            db.refresh(empresa)
            print(f"✅ Empresa creada: {empresa.nombre}")

        # 2. Admin
        admin = db.query(models.Usuario).filter(
            models.Usuario.email == admin_email,
            models.Usuario.empresa_id == empresa.id,
        ).first()
        if not admin:
            admin = models.Usuario(
                email=admin_email,
                nombre="Admin",
                apellido="Sistema",
                hashed_password=get_password_hash(admin_password),
                esta_activo=True,
                rol="admin",
                empresa_id=empresa.id,
            )
            db.add(admin)
            db.commit()
            print("✅ Admin creado")
        else:
            print("⚠️ Admin ya existe")
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_inicial()