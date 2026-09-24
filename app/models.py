from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from .database import Base,engine


class Empresa(Base):
    __tablename__ = "empresas"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    nit = Column(String, unique=True, nullable=False)  # NIT o identificación
    direccion = Column(String, nullable=True)
    telefono = Column(String, nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    usuarios = relationship("Usuario", back_populates="empresa")
    transacciones = relationship("Transaccion", back_populates="empresa")




class TipoTransaccion(str, enum.Enum):
    ENVIADA = "enviada"
    RECIBIDA = "recibida"

class EstadoTransaccion(str, enum.Enum):
    PENDIENTE = "pendiente"
    CONFIRMADA = "confirmada"
    RECHAZADA = "rechazada"
    

#usuario
class Usuario(Base):
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    nombre = Column(String, nullable=False)
    apellido = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    esta_activo = Column(Boolean, default=True)
    rol = Column(String, default="usuario")  # 👈 NUEVO: "admin" o "usuario"
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)  # 👈 NUEVO
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relación con transacciones
    empresa = relationship("Empresa", back_populates="usuarios")
    transacciones = relationship("Transaccion", back_populates="usuario")
    opiniones = relationship("Opinion", back_populates="usuario", cascade="all, delete-orphan")

class Transaccion(Base):
    __tablename__ = "transacciones"
    
    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)  # 👈 NUEVO
   
    # Datos del usuario
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    
    # Datos de la transacción
    banco = Column(String, nullable=False)
    fecha = Column(String, nullable=False)
    beneficiario = Column(String, nullable=False)
    ordenante = Column(String, nullable=False)
    monto = Column(Float, nullable=False)
    moneda = Column(String, nullable=False)
    numero_transaccion = Column(String, unique=True, nullable=False, index=True)
    
    # Clasificación del usuario
    tipo = Column(Enum(TipoTransaccion), nullable=False)
    estado = Column(Enum(EstadoTransaccion), default=EstadoTransaccion.PENDIENTE)
    
    # Metadatos
    descripcion = Column(String, default="")
    etiquetas = Column(String, default="")  # JSON string de etiquetas
    fecha_procesamiento = Column(DateTime(timezone=True), server_default=func.now())
    fecha_confirmacion = Column(DateTime(timezone=True), nullable=True)
    
    # Relación
    empresa = relationship("Empresa", back_populates="transacciones")
    usuario = relationship("Usuario", back_populates="transacciones")
   

class Etiqueta(Base):
    __tablename__ = "etiquetas"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, nullable=False)
    color = Column(String, default="#007bff")
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    
    # Relación muchos a muchos con transacciones
    transacciones = relationship("Transaccion", secondary="transaccion_etiquetas", backref="etiquetas_rel")

class TransaccionEtiqueta(Base):
    __tablename__ = "transaccion_etiquetas"
    
    transaccion_id = Column(Integer, ForeignKey("transacciones.id"), primary_key=True)
    etiqueta_id = Column(Integer, ForeignKey("etiquetas.id"), primary_key=True)


# models.py - Agregar esta clase

class Opinion(Base):
    __tablename__ = "opiniones"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    usuario_nombre = Column(String, nullable=False)
    titulo = Column(String, nullable=False)
    mensaje = Column(String, nullable=False)
    puntuacion = Column(Integer, default=5)  # 1-5 estrellas
    fecha = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relación
    usuario = relationship("Usuario", back_populates="opiniones")
    
    
    
class StatusSolicitud(str, enum.Enum):
    PENDING = "pending"
    CONTACTED = "contacted"
    CONVERTED = "converted"

class ContractRequest(Base):
    __tablename__ = "contract_requests"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False, index=True)   # índice para búsquedas rápidas
    phone = Column(String, nullable=True)
    company = Column(String, nullable=True)
    message = Column(String, nullable=True)   # TEXT en SQLite
    plan = Column(String, nullable=True)      # "Básico", "Premium", "Empresarial"
    status = Column(Enum(StatusSolicitud), default=StatusSolicitud.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    # (Opcional) Si luego quieres relacionar con un usuario o empresa cuando se convierta
    # usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    # empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)


# Crear las tablas
def create_tables():
    Base.metadata.create_all(bind=engine)