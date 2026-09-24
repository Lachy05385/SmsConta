from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.models import ContractRequest, StatusSolicitud
from app.database import get_db
from app.schemas import ContratoRequest

#router = APIRouter()
router = APIRouter(prefix="/api", tags=["contratos"])
# Esquema de validación

@router.post("/contrato")
def solicitar_contrato(data: ContratoRequest, db: Session = Depends(get_db)):
    nueva_solicitud = ContractRequest(
        full_name=data.nombre,
        email=data.email,
        phone=data.telefono,
        company=data.empresa,
        message=data.mensaje,
        plan=data.plan,
        status=StatusSolicitud.PENDING
    )
    
    
    
    
    print("Procesar Solicitud de Contrato")
    print(nueva_solicitud.full_name)
    db.add(nueva_solicitud)
    db.commit()
    db.refresh(nueva_solicitud)
    return {"status": "ok", "message": "Solicitud recibida", "id": nueva_solicitud.id}