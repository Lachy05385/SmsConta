from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from .. import models

router = APIRouter(prefix="/api", tags=["stats"])

@router.get("/stats")
def obtener_estadisticas_publicas(db: Session = Depends(get_db)):
    """
    Endpoint público para la landing page.
    Devuelve el conteo de empresas y las últimas opiniones positivas.
    NO expone datos sensibles.
    """
    # Contar empresas
    total_empresas = db.query(func.count(models.Empresa.id)).scalar() or 0
    
    # Contar usuarios activos (opcional, si quieres mostrarlo también)
    total_usuarios = db.query(func.count(models.Usuario.id)).filter(
        models.Usuario.esta_activo == True
    ).scalar() or 0
    
    # Obtener las 3 opiniones más recientes con puntuación >= 4
    opiniones = (
        db.query(models.Opinion)
        .filter(models.Opinion.puntuacion >= 4)
        .order_by(models.Opinion.fecha.desc())
        .limit(3)
        .all()
    )
    
    return {
        "total_clientes": total_empresas,
        "total_usuarios": total_usuarios,
        "opiniones": [
            {
                "nombre": op.usuario_nombre,
                "titulo": op.titulo,
                "mensaje": op.mensaje,
                "puntuacion": op.puntuacion
            }
            for op in opiniones
        ]
    }