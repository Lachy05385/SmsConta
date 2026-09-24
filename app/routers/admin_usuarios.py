# routers/admin_usuarios.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.auth import get_current_active_user, get_current_user
import sys
import os

# Agregar el directorio padre para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_db
import models
import schemas
import crud

router = APIRouter(prefix="/admin", tags=["Administración"])

@router.post("/usuarios", response_model=schemas.UserResponse)
@debug_endpoint
def crear_usuario_por_admin(
    usuario: schemas.UserCreate,
    current_user: models.Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Crear nuevo usuario (solo administradores)"""
    
    debug_print(f"Iniciando creación de usuario - Email: {usuario.email}")
    
    # Verificar que quien crea es admin
    if current_user.rol != "admin":
        debug_print(f"Permiso denegado - Rol actual: {current_user.rol}")
        raise HTTPException(status_code=403, detail="No tienes permisos de administrador")
    
    # Verificar si el email ya existe
    db_user = crud.get_user_by_email(db, email=usuario.email)
    if db_user:
        debug_print(f"Email ya existe: {usuario.email}")
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    # Validar que el rol sea válido
    roles_validos = ["usuario", "contador", "admin"]
    rol_valido = usuario.rol if hasattr(usuario, 'rol') and usuario.rol in roles_validos else "usuario"
    debug_print(f"Rol asignado: {rol_valido}")
    
    # Validar contraseña
    if len(usuario.password) < 5:
        debug_print(f"Contraseña demasiado corta: {len(usuario.password)} caracteres")
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 5 caracteres")
    
    # Crear usuario
    nuevo_usuario = models.Usuario(
        email=usuario.email,
        nombre=usuario.nombre,
        apellido=usuario.apellido,
        hashed_password=get_password_hash(usuario.password),  # Asegúrate de importar esta función
        esta_activo=True,
        rol=rol_valido,
        empresa_id=usuario.empresa_id
    )
    
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    
    debug_print(f"Usuario creado exitosamente - ID: {nuevo_usuario.id}")
    return nuevo_usuario


@router.delete("/usuarios/{usuario_id}", response_model=dict)
@debug_endpoint
def eliminar_usuario_logicamente(
    usuario_id: int,
    current_user: models.Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Borrado lógico de usuario (solo administradores)
    El usuario se marca como inactivo pero permanece en la BD
    """
    debug_print(f"Intentando borrado lógico de usuario ID: {usuario_id}")
    
    # Verificar permisos
    if current_user.rol != "admin":
        raise HTTPException(
            status_code=403, 
            detail="No tienes permisos de administrador"
        )
    
    # Buscar usuario
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Evitar auto-eliminación
    if usuario.id == current_user.id:
        raise HTTPException(
            status_code=400, 
            detail="No puedes eliminar tu propio usuario"
        )
    
    # Verificar si ya está eliminado
    if not usuario.esta_activo:
        raise HTTPException(
            status_code=400, 
            detail="El usuario ya está inactivo"
        )
    
    try:
        # Borrado lógico
        usuario.esta_activo = False
        usuario.fecha_eliminacion = datetime.now()  # Necesitas agregar este campo al modelo
        usuario.eliminado_por_id = current_user.id  # Campo opcional
        
        db.commit()
        db.refresh(usuario)
        
        debug_print(f"✅ Usuario {usuario_id} marcado como inactivo")
        
        return {
            "message": "Usuario desactivado exitosamente",
            "usuario": {
                "id": usuario.id,
                "email": usuario.email,
                "nombre": usuario.nombre,
                "apellido": usuario.apellido,
                "estado": "inactivo",
                "fecha_eliminacion": usuario.fecha_eliminacion
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al desactivar usuario: {str(e)}")