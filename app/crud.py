from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models, schemas
from app.utils import parse_transaccion_texto
from datetime import datetime
import json
import re
from typing import List, Optional
from app.auth import get_password_hash, get_current_user 
from fastapi.exceptions import HTTPException

def get_user(db: Session, user_id: int):
    """Obtiene un usuario por su ID"""
    return db.query(models.Usuario).filter(models.Usuario.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    """Obtiene un usuario por su email"""
    return db.query(models.Usuario).filter(models.Usuario.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    """Obtiene lista de usuarios"""
    return db.query(models.Usuario).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate):
    """Crea un nuevo usuario"""
    hashed_password = get_password_hash(user.password)
    rol_valido = user.rol if user.rol in ["usuario", "contador", "admin"] else "usuario"
    db_user = models.Usuario(
        email=user.email,
        nombre=user.nombre,
        apellido=user.apellido,
        hashed_password=hashed_password,
        esta_activo=True,
        rol = rol_valido
        
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user



def create_transaccion(db: Session, transaccion: schemas.TransaccionCreate, usuario_id: int, empresa_id:int):
    """
    Crear una transacción manualmente asociada al usuario
    """
    
    
    estado_valor = getattr(transaccion, 'estado', models.EstadoTransaccion.PENDIENTE)
    db_transaccion = models.Transaccion(
        usuario_id=usuario_id,
        empresa_id=empresa_id,
        banco=transaccion.banco,
        fecha=transaccion.fecha,
        beneficiario=transaccion.beneficiario,
        ordenante=transaccion.ordenante,
        monto=transaccion.monto,
        moneda=transaccion.moneda,
        numero_transaccion=transaccion.numero_transaccion,
        tipo=transaccion.tipo,
        estado=estado_valor,
        descripcion=transaccion.descripcion or "",
        etiquetas=json.dumps(transaccion.etiquetas) if transaccion.etiquetas else "[]"
    )
    
    db.add(db_transaccion)
    db.commit()
    db.refresh(db_transaccion)
    return db_transaccion

def parse_and_create_transaccion(db: Session, texto: str, tipo: str, usuario_id: int, descripcion: Optional[str] = None):
    """
    Crear transacción desde texto asociada al usuario
    """
    # Parsear el texto
    datos = parse_transaccion_texto(texto)
    
    # Crear transacción
    db_transaccion = models.Transaccion(
        usuario_id=usuario_id,
        banco=datos.get("banco", ""),
        fecha=datos.get("fecha", datetime.now().strftime("%Y-%m-%d")),
        beneficiario=datos.get("beneficiario", ""),
        ordenante=datos.get("ordenante", ""),
        monto=datos.get("monto", 0),
        moneda=datos.get("moneda", "EUR"),
        numero_transaccion=datos["numero_transaccion"],
        tipo=tipo,
        estado=models.EstadoTransaccion.PENDIENTE,
        descripcion=descripcion or datos.get("concepto", ""),
        etiquetas="[]"
    )
    
    db.add(db_transaccion)
    db.commit()
    db.refresh(db_transaccion)
    return db_transaccion

def get_transacciones_usuario(
    db: Session, 
    usuario_id: int, 
    skip: int = 0, 
    limit: int = 100,
    tipo: Optional[str] = None,
    estado: Optional[str] = None,
    banco: Optional[str] = None,
    fecha_inicio: Optional[str] = None,  # 👈 NUEVO
    fecha_fin: Optional[str] = None       # 👈 NUEVO
):
    query = db.query(models.Transaccion).filter(
        models.Transaccion.usuario_id == usuario_id
    )
    
    if tipo:
        query = query.filter(models.Transaccion.tipo == tipo)
    if estado:
        query = query.filter(models.Transaccion.estado == estado)
    if banco:
        query = query.filter(models.Transaccion.banco.ilike(f"%{banco}%"))
    
    # 👇 NUEVOS FILTROS DE FECHA
    if fecha_inicio:
        query = query.filter(models.Transaccion.fecha >= fecha_inicio)
    if fecha_fin:
        query = query.filter(models.Transaccion.fecha <= fecha_fin)
    
    query = query.order_by(models.Transaccion.fecha.desc())
    
    return query.offset(skip).limit(limit).all()
def get_transaccion(db: Session, transaccion_id: int, usuario_id: int):
    """
    Obtener una transacción específica verificando que pertenezca al usuario
    """
    return db.query(models.Transaccion).filter(
        models.Transaccion.id == transaccion_id,
        models.Transaccion.usuario_id == usuario_id
    ).first()

def update_transaccion(db: Session, transaccion_id: int, usuario_id: int, transaccion_update: schemas.TransaccionUpdate):
    """
    Actualizar transacción verificando propiedad
    """
    # Buscar la transacción
    db_transaccion = db.query(models.Transaccion).filter(
        models.Transaccion.id == transaccion_id,
        models.Transaccion.usuario_id == usuario_id
    ).first()
    
    if not db_transaccion:
        return None
    
    # Obtener solo los campos que fueron enviados (excluir None)
    update_data = transaccion_update.model_dump(exclude_unset=True)
    
    #  CONVERTIR etiquetas de lista a JSON string
    
    '''if 'etiquetas' in update_data and isinstance(update_data['etiquetas'], list):
        import json
        update_data['etiquetas'] = json.dumps(update_data['etiquetas'])'''
       
    
     # Actualizar campo por campo
    for key, value in update_data.items():
        setattr(db_transaccion, key, value)
    
    print(f"📝 Actualizando campos: {update_data.keys()}")  # Debug
    
  
    
    try:
        db.commit()
        db.refresh(db_transaccion)
        print("✅ Cambios guardados en BD")
        return db_transaccion
    except Exception as e:
        db.rollback()
        print(f"❌ Error al guardar: {e}")
        raise

def confirmar_transaccion(db: Session, transaccion_id: int, usuario_id: int):
    from sqlalchemy import update
    from sqlalchemy.orm import joinedload

    print("=" * 60)
    print(f"🔍 CONFIRMAR - transaccion_id={transaccion_id}, usuario_id={usuario_id}")

    # 1. Verificar que la transacción existe
    db_transaccion = db.query(models.Transaccion).filter(
        models.Transaccion.id == transaccion_id
    ).first()

    if not db_transaccion:
        print(f"❌ NO existe transacción con id={transaccion_id}")
        return None

    print(f"✅ Transacción encontrada:")
    print(f"   - id: {db_transaccion.id}")
    print(f"   - estado: {repr(db_transaccion.estado)}")
    print(f"   - usuario_id: {db_transaccion.usuario_id}")
    print(f"   - empresa_id: {db_transaccion.empresa_id}")

    # 2. Verificar permisos
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario:
        print(f"❌ NO existe usuario con id={usuario_id}")
        return None

    print(f"✅ Usuario: {usuario.email}, rol={usuario.rol}, empresa_id={usuario.empresa_id}")

    # 3. Hacer UPDATE explícito
    try:
        stmt = (
            update(models.Transaccion)
            .where(models.Transaccion.id == transaccion_id)
            .values(
                estado="confirmada",
                fecha_confirmacion=datetime.now()
            )
        )
        result = db.execute(stmt)
        print(f"📊 UPDATE afectó {result.rowcount} filas")
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"❌ Error en UPDATE: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise

    # 4. Recargar
    db_transaccion = db.query(models.Transaccion).filter(
        models.Transaccion.id == transaccion_id
    ).first()

    print(f"📊 Estado después del UPDATE: {repr(db_transaccion.estado)}")
    print("=" * 60)

    return db_transaccion

def get_resumen_transacciones(db: Session, usuario_id: int):
    """
    Obtener resumen de transacciones del usuario
    """
    transacciones = db.query(models.Transaccion).filter(
        models.Transaccion.usuario_id == usuario_id
    ).all()
    
    # Calcular resúmenes
    total_enviadas = sum(t.monto for t in transacciones if t.tipo == models.TipoTransaccion.ENVIADA)
    total_recibidas = sum(t.monto for t in transacciones if t.tipo == models.TipoTransaccion.RECIBIDA)
    pendientes = len([t for t in transacciones if t.estado == models.EstadoTransaccion.PENDIENTE])
    confirmadas = len([t for t in transacciones if t.estado == models.EstadoTransaccion.CONFIRMADA])
    
    # Agrupar por banco
    bancos = {}
    for t in transacciones:
        if t.banco not in bancos:
            bancos[t.banco] = {"cantidad": 0, "monto_total": 0}
        bancos[t.banco]["cantidad"] += 1
        bancos[t.banco]["monto_total"] += t.monto
    
    return {
        "total_transacciones": len(transacciones),
        "total_enviadas": total_enviadas,
        "total_recibidas": total_recibidas,
        "balance": total_recibidas - total_enviadas,
        "pendientes": pendientes,
        "confirmadas": confirmadas,
        "bancos": bancos,
        "transacciones_recientes": transacciones[:5]  # Últimas 5
    }

def buscar_transacciones(db: Session, usuario_id: int, query: str):
    """
    Buscar transacciones por texto (beneficiario, ordenante, concepto, etc)
    """
    return db.query(models.Transaccion).filter(
        models.Transaccion.usuario_id == usuario_id,
        (models.Transaccion.beneficiario.ilike(f"%{query}%") |
         models.Transaccion.ordenante.ilike(f"%{query}%") |
         models.Transaccion.descripcion.ilike(f"%{query}%") |
         models.Transaccion.numero_transaccion.ilike(f"%{query}%"))
    ).order_by(models.Transaccion.fecha_procesamiento.desc()).all()
    
    
def get_user_by_email(db: Session, email: str):
    """
    Obtiene un usuario por su email
    """
    print(f"🔍 Buscando usuario con email: {email}")
    user = db.query(models.Usuario).filter(models.Usuario.email == email).first()
    if user:
        print(f"✅ Usuario encontrado: {user.email}")
    else:
        print(f"❌ Usuario no encontrado: {email}")
    return user

def get_transacciones_por_fecha(
    db: Session, 
    usuario_id: int, 
    fecha_inicio: str, 
    fecha_fin: str
):
    """
    Obtiene las transacciones Todas de un usuario en un rango de fechas
    Las fechas deben estar en formato DD/MM/YYYY
    """
    transacciones = db.query(models.Transaccion).filter(
        models.Transaccion.usuario_id == usuario_id,
        models.Transaccion.fecha >= fecha_inicio,
        models.Transaccion.fecha <= fecha_fin
    ).order_by(models.Transaccion.fecha.desc()).all()
    
    return transacciones




def get_transacciones_recibidas_por_fecha(
    db: Session, 
    usuario_id: int, 
    fecha_inicio: str, 
    fecha_fin: str
):
    """
    Obtiene las transacciones RECIBIDAS de un usuario en un rango de fechas
    Las fechas deben estar en formato DD/MM/YYYY
    """
    transacciones = db.query(models.Transaccion).filter(
        models.Transaccion.usuario_id == usuario_id,
        models.Transaccion.tipo == "recibida",  # Solo recibidas
        models.Transaccion.fecha >= fecha_inicio,
        models.Transaccion.fecha <= fecha_fin
    ).order_by(models.Transaccion.fecha.desc()).all()
    print("recibidas por fecha ")
    return transacciones

def get_transacciones_enviadas_por_fecha(
    db: Session,
    usuario_id: int,
    fecha_inicio: str,
    fecha_fin: str
):
    """
    Obtiene las transacciones ENVIADAS de un usuario en un rango de fechas
    Las fechas deben estar en formato DD/MM/YYYY
    """
    print(f"🔍 Buscando transacciones ENVIADAS del usuario {usuario_id}")
    print(f"📅 Rango: {fecha_inicio} - {fecha_fin}")
    
    # Validar formato de fechas (opcional pero recomendado)
    try:
        # Verificar que tengan formato DD/MM/YYYY
        dia_i, mes_i, año_i = map(int, fecha_inicio.split('/'))
        dia_f, mes_f, año_f = map(int, fecha_fin.split('/'))
        
        # Crear objetos datetime para comparar (opcional)
        from datetime import datetime
        fecha_inicio_dt = datetime(año_i, mes_i, dia_i)
        fecha_fin_dt = datetime(año_f, mes_f, dia_f)
        
        if fecha_inicio_dt > fecha_fin_dt:
            raise ValueError("La fecha de inicio no puede ser mayor que la fecha fin")
            
    except ValueError as e:
        raise ValueError(f"Formato de fecha inválido. Use DD/MM/YYYY. Error: {str(e)}")
    
    # Consulta a la base de datos
    transacciones = db.query(models.Transaccion).filter(
        models.Transaccion.usuario_id == usuario_id,
        models.Transaccion.tipo == "enviada",  # Solo enviadas
        models.Transaccion.fecha >= fecha_inicio,
        models.Transaccion.fecha <= fecha_fin
    ).order_by(models.Transaccion.fecha.desc()).all()
    
    print(f"✅ Encontradas {len(transacciones)} transacciones")
    return transacciones