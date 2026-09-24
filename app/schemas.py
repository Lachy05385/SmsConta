# app/schemas.py
from pydantic import BaseModel, field_validator, EmailStr, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import re
import json


# ====================== ENUMERACIONES ======================
class TipoTransaccion(str, Enum):
    ENVIADA = "enviada"
    RECIBIDA = "recibida"

class EstadoTransaccion(str, Enum):
    PENDIENTE = "pendiente"
    CONFIRMADA = "confirmada"
    RECHAZADA = "rechazada"

# ====================== ESQUEMAS DE AUTENTICACIÓN ======================
class EmpresaBase(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    nit: str = Field(..., min_length=3, max_length=50)
    direccion: Optional[str] = Field(None, max_length=200)
    telefono: Optional[str] = Field(None, max_length=20)

class EmpresaCreate(EmpresaBase):
    pass

class EmpresaResponse(EmpresaBase):
    id: int
    fecha_creacion: datetime
    
    model_config = ConfigDict(from_attributes=True)



class UserCreate(BaseModel):
    email: EmailStr = Field(..., description="Email del usuario")
    nombre: str = Field(..., min_length=2, max_length=50, 
                       description="Nombre del usuario (2-50 caracteres)")
    apellido: str = Field(..., min_length=2, max_length=50,
                         description="Apellido del usuario (2-50 caracteres)")
    password: str = Field(..., min_length=6, max_length=128,
                         description="Contraseña (mínimo 6 caracteres)")
    rol: Optional[str] = "usuario"
    empresa_id: Optional[int] = None
    
    @field_validator('nombre', 'apellido')
    @classmethod
    def validar_nombre_apellido(cls, v: str) -> str:
        """Validar que solo contenga letras y espacios"""
        v = v.strip()
        if not v.replace(" ", "").replace("-", "").isalpha():
            raise ValueError('Solo se permiten letras, espacios y guiones')
        if len(v) < 2:
            raise ValueError('Debe tener al menos 2 caracteres')
        return v.title()
    
    @field_validator('email')
    @classmethod
    def normalizar_email(cls, v: str) -> str:
        """Normalizar email a minúsculas"""
        return v.strip().lower()

class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="Email del usuario")
    password: str = Field(..., min_length=1, max_length=128,
                         description="Contraseña del usuario")

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    nombre: str
    apellido: str
    esta_activo: bool
    rol: str
    empresa_id: int
    fecha_creacion: datetime
    
    empresa: Optional[EmpresaResponse] = None
    
    model_config = ConfigDict(from_attributes=True)
    

# schemas.py - Agregar este schema

class UserUpdate(BaseModel):
    """Schema para actualizar usuario (todos los campos opcionales)"""
    nombre: Optional[str] = Field(None, min_length=2, max_length=50)
    apellido: Optional[str] = Field(None, min_length=2, max_length=50)
    rol: Optional[str] = None
    empresa_id: Optional[int] = None
    esta_activo: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6)
    
    

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = Field(1800, description="Tiempo de expiración en segundos")

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None

# ====================== ESQUEMAS DE TRANSACCIONES ======================
class TransaccionBase(BaseModel):
    banco: str = Field(..., min_length=2, max_length=100,
                      description="Nombre del banco")
    fecha: str = Field(..., description="Fecha en formato DD/MM/YYYY")
    beneficiario: str = Field(..., min_length=4, max_length=50,
                            description="Número de cuenta del beneficiario")
    ordenante: str = Field(..., min_length=4, max_length=50,
                          description="Número de cuenta del ordenante")
    monto: float = Field(..., gt=0, le=10000000, description="Monto de la transacción (0-10M)")
    moneda: str = Field(..., min_length=1, max_length=10,
                       description="Moneda (CUP, USD, EUR, MLC)")
    numero_transaccion: str = Field(..., min_length=4, max_length=50,
                                   description="Número único de transacción")
    
    @field_validator('fecha')
    @classmethod
    def validar_fecha(cls, v: str) -> str:
        """Validar formato DD/MM/YYYY"""
        v = v.strip()
        
        # Validar formato básico
        pattern = r"^\d{2}/\d{2}/\d{4}$"
        if not re.match(pattern, v):
            raise ValueError('Formato de fecha inválido. Use DD/MM/YYYY')
        
        # Validar fecha básica
        try:
            day, month, year = map(int, v.split('/'))
            if not (1 <= day <= 31 and 1 <= month <= 12 and year >= 2000):
                raise ValueError('Fecha inválida')
        except ValueError:
            raise ValueError('Fecha inválida')
        
        return v
    
    @field_validator('monto')
    @classmethod
    def validar_monto(cls, v: float) -> float:
        """Validar monto"""
        if v <= 0:
            raise ValueError('El monto debe ser mayor que cero')
        return round(v, 2)
    
    @field_validator('moneda')
    @classmethod
    def validar_moneda(cls, v: str) -> str:
        """Validar moneda"""
        monedas_validas = ['CUP', 'USD', 'EUR', 'MLC']
        v_upper = v.strip().upper()
        
        if v_upper not in monedas_validas:
            raise ValueError(f'Moneda no válida. Use: {", ".join(monedas_validas)}')
        
        return v_upper
   

class TransaccionCreate(TransaccionBase):
    tipo: TipoTransaccion = Field(..., description="Tipo de transacción")
    descripcion: Optional[str] = Field(default="", max_length=200,
                                      description="Descripción opcional")
    etiquetas: Optional[List[str]] = Field(default_factory=list,
                                          description="Lista de etiquetas")
    
    @field_validator('descripcion')
    @classmethod
    def validar_descripcion(cls, v: Optional[str]) -> str:
        """Validar descripción"""
        if v is None:
            return ""
        v = v.strip()
        if len(v) > 200:
            raise ValueError('La descripción no puede exceder 200 caracteres')
        return v

class TransaccionParseRequest(BaseModel):
    texto: str = Field(..., min_length=10, max_length=4000,
                      description="Texto de la transacción bancaria")
    tipo: TipoTransaccion = Field(..., description="Tipo de transacción")
    descripcion: Optional[str] = Field(default="", max_length=200,
                                      description="Descripción opcional")

class TransaccionUpdate(BaseModel):
    """Campos que se pueden actualizar (todos opcionales)"""
    tipo: Optional[TipoTransaccion] = None
    estado: Optional[EstadoTransaccion] = None
    descripcion: Optional[str] = None
    etiquetas: Optional[List[str]] = None
    monto: Optional[float] = Field(None, gt=0)           # 👈 Monto
    fecha: Optional[str] = None                          # 👈 Fecha
    banco: Optional[str] = None                          # 👈 Banco
    beneficiario: Optional[str] = None                   # 👈 Beneficiario
    ordenante: Optional[str] = None                      # 👈 Ordenante
    moneda: Optional[str] = None                         # 👈 Moneda
    
    @field_validator('descripcion')
    @classmethod
    def validar_descripcion(cls, v: Optional[str]) -> Optional[str]:
        """Validar descripción"""
        if v is None:
            return None
        v = v.strip()
        if len(v) > 200:
            raise ValueError('La descripción no puede exceder 200 caracteres')
        return v if v else None
    
class EstadoUpdate(BaseModel):
    estado: str

class TransaccionResponse(TransaccionBase):
    id: int
    usuario_id: int
    empresa_id: int
    tipo: TipoTransaccion
    estado: EstadoTransaccion
    descripcion: str
    etiquetas: List[str]  # Debe ser List, no str
    fecha_procesamiento: datetime
    fecha_confirmacion: Optional[datetime] = None
    usuario: Optional[UserResponse] = None
    
    
    @field_validator('etiquetas', mode='before')
    @classmethod
    def parse_etiquetas(cls, v):
        """Convierte string JSON a lista si es necesario"""
        if isinstance(v, str):
            try:
                # Si es un string JSON, parsearlo
                return json.loads(v)
            except:
                # Si falla, devolver lista vacía
                return []
        # Si ya es lista, devolverla
        return v or []
    
    
    
class ContratoRequest(BaseModel):
    nombre: str
    email: EmailStr
    telefono: Optional[str] = None
    empresa: Optional[str] = None
    mensaje: Optional[str] = None
    plan: Optional[str] = None   # "Básico", "Premium", "Empresarial"

    
    model_config = ConfigDict(from_attributes=True)
    


# ====================== ESQUEMAS DE REPORTES ======================
class ReporteRequest(BaseModel):
    fecha_inicio: Optional[str] = Field(None, description="Fecha inicio (DD/MM/YYYY)")
    fecha_fin: Optional[str] = Field(None, description="Fecha fin (DD/MM/YYYY)")
    tipo: Optional[TipoTransaccion] = Field(None, description="Filtrar por tipo")
    estado: Optional[EstadoTransaccion] = Field(None, description="Filtrar por estado")
    banco: Optional[str] = Field(None, description="Filtrar por banco")

class ResumenTransacciones(BaseModel):
    total_enviadas: float = 0.0
    total_recibidas: float = 0.0
    total_pendientes: int = 0
    total_confirmadas: int = 0
    total_rechazadas: int = 0
    total_transacciones: int = 0
    transacciones_por_banco: Dict[str, int] = {}
    transacciones_por_mes: Dict[str, int] = {}
    transacciones_por_estado: Dict[str, int] = {}

# ====================== ESQUEMAS DE ETIQUETAS ======================
class EtiquetaCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=20,
                       description="Nombre de la etiqueta")
    color: Optional[str] = Field(default="#007bff",
                                description="Color en formato hex (#RRGGBB)")
    
    @field_validator('nombre')
    @classmethod
    def validar_nombre_etiqueta(cls, v: str) -> str:
        """Validar nombre de etiqueta"""
        v = v.strip()
        if not v:
            raise ValueError('El nombre no puede estar vacío')
        if len(v) > 20:
            raise ValueError('El nombre no puede exceder 20 caracteres')
        return v.title()
    
    @field_validator('color')
    @classmethod
    def validar_color(cls, v: Optional[str]) -> str:
        """Validar color"""
        if v is None:
            return "#007bff"
        
        v = v.strip()
        
        # Validar formato hex básico
        if not re.match(r'^#[0-9a-fA-F]{3,6}$', v):
            raise ValueError('Color inválido. Use formato hex (#RGB o #RRGGBB)')
        
        return v

class EtiquetaResponse(BaseModel):
    id: int
    nombre: str
    color: str
    usuario_id: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)

# ====================== ESQUEMAS PARA ESTADÍSTICAS ======================
class EstadisticasUsuario(BaseModel):
    total_transacciones: int
    transacciones_mes_actual: int
    saldo_promedio_recibido: float
    saldo_promedio_enviado: float
    banco_mas_utilizado: Optional[str] = None
    mes_mas_activo: Optional[str] = None

# ====================== ESQUEMAS PARA BÚSQUEDA ======================
class BusquedaTransacciones(BaseModel):
    query: Optional[str] = Field(None, min_length=1, max_length=100,
                                description="Texto a buscar")
    fecha_desde: Optional[str] = Field(None, description="Fecha desde (DD/MM/YYYY)")
    fecha_hasta: Optional[str] = Field(None, description="Fecha hasta (DD/MM/YYYY)")
    monto_minimo: Optional[float] = Field(None, gt=0, description="Monto mínimo")
    monto_maximo: Optional[float] = Field(None, gt=0, description="Monto máximo")
    limit: int = Field(50, ge=1, le=200, description="Límite de resultados")
    offset: int = Field(0, ge=0, description="Desplazamiento")

# ====================== ESQUEMA PARA CAMBIO DE CONTRASEÑA ======================
class CambioPassword(BaseModel):
    password_actual: str = Field(..., min_length=6, max_length=128,
                                description="Contraseña actual")
    password_nueva: str = Field(..., min_length=6, max_length=128,
                               description="Nueva contraseña")
    confirmar_password: str = Field(..., min_length=6, max_length=128,
                                   description="Confirmar nueva contraseña")
    
    @field_validator('password_nueva')
    @classmethod
    def validar_password_nueva(cls, v: str, info) -> str:
        """Validar nueva contraseña"""
        v = v.strip()
        
        # Verificar que no sea igual a la actual
        if 'password_actual' in info.data and v == info.data['password_actual']:
            raise ValueError('La nueva contraseña debe ser diferente a la actual')
        
        return v
    
    @field_validator('confirmar_password')
    @classmethod
    def validar_confirmacion_password(cls, v: str, info) -> str:
        """Verificar que las contraseñas coincidan"""
        v = v.strip()
        if 'password_nueva' in info.data and v != info.data['password_nueva']:
            raise ValueError('Las contraseñas no coinciden')
        return v

# ====================== ESQUEMA PARA ACTUALIZACIÓN DE PERFIL ======================
class ActualizarPerfil(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2, max_length=50,
                                 description="Nuevo nombre")
    apellido: Optional[str] = Field(None, min_length=2, max_length=50,
                                   description="Nuevo apellido")

# ====================== ESQUEMAS DE RESPUESTA ======================
class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None
    field: Optional[str] = None

class SuccessResponse(BaseModel):
    message: str
    data: Optional[Dict[str, Any]] = None

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    pages: int
    size: int

# ====================== ESQUEMA PARA NOTIFICACIONES ======================
class NotificacionBase(BaseModel):
    titulo: str = Field(..., max_length=100)
    mensaje: str = Field(..., max_length=500)
    tipo: str = Field("info")

class NotificacionResponse(NotificacionBase):
    id: int
    usuario_id: int
    leida: bool
    fecha_creacion: datetime
    
    model_config = ConfigDict(from_attributes=True)

# ====================== ESQUEMA PARA RESPONSES DE API ======================
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ListaTransaccionesResponse(BaseModel):
    transacciones: List[TransaccionResponse]
    total: int
    pagina: int
    total_paginas: int

# ====================== ESQUEMAS PARA IMPORTACIÓN ======================
class ImportTransaccionesRequest(BaseModel):
    transacciones: List[TransaccionCreate]

# ====================== ESQUEMAS PARA EXPORTACIÓN ======================
class ExportTransaccionesRequest(BaseModel):
    formato: str = Field("json", pattern="^(json|csv)$")
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None
    incluir_campos: List[str] = Field(
        default_factory=lambda: [
            "fecha", "banco", "beneficiario", "ordenante", 
            "monto", "moneda", "tipo", "estado", "descripcion"
        ]
    )

# ====================== ESQUEMAS PARA DASHBOARD ======================
class DashboardStats(BaseModel):
    total_balance: float
    ingresos_mes_actual: float
    egresos_mes_actual: float
    transacciones_pendientes: int
    top_bancos: List[Dict[str, Any]]
    ultimas_transacciones: List[TransaccionResponse]

# ====================== ESQUEMA PARA CONFIRMACIÓN MASIVA ======================
class ConfirmacionMasivaRequest(BaseModel):
    transaccion_ids: List[int] = Field(..., min_items=1, max_items=100)

class ConfirmacionMasivaResponse(BaseModel):
    confirmadas: int
    fallidas: int
    detalles: List[Dict[str, Any]]

# ====================== ESQUEMA PARA FILTROS AVANZADOS ======================
class FiltroAvanzadoTransacciones(BaseModel):
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None
    monto_min: Optional[float] = None
    monto_max: Optional[float] = None
    bancos: Optional[List[str]] = None
    tipos: Optional[List[TipoTransaccion]] = None
    estados: Optional[List[EstadoTransaccion]] = None
    etiquetas: Optional[List[str]] = None
    ordenar_por: Optional[str] = Field("fecha_procesamiento", 
                                      pattern="^(fecha|monto|banco|fecha_procesamiento)$")
    orden: Optional[str] = Field("desc", pattern="^(asc|desc)$")

# ====================== ESQUEMA PARA SUGERENCIAS ======================
class SugerenciaEtiqueta(BaseModel):
    transaccion_id: int
    etiquetas_sugeridas: List[str]
    confianza: float

# ====================== ESQUEMA PARA BACKUP ======================
class BackupRequest(BaseModel):
    incluir_usuarios: bool = Field(False, description="Incluir datos de usuarios")
    incluir_transacciones: bool = Field(True, description="Incluir transacciones")
    incluir_etiquetas: bool = Field(True, description="Incluir etiquetas")
    formato: str = Field("json", pattern="^(json|sql)$")

class BackupResponse(BaseModel):
    backup_id: str
    fecha_creacion: datetime
    tamaño_bytes: int
    url_descarga: Optional[str] = None
    checksum: str

# ====================== ESQUEMA PARA RESTAURACIÓN ======================
class RestoreRequest(BaseModel):
    backup_id: str
    confirmar: bool = Field(False, description="Confirmar restauración (operación destructiva)")

# ====================== ESQUEMA PARA AUDITORÍA ======================
class AuditoriaEvento(BaseModel):
    id: int
    usuario_id: Optional[int]
    tipo_evento: str
    descripcion: str
    ip_origen: Optional[str]
    user_agent: Optional[str]
    fecha_evento: datetime
    metadata: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(from_attributes=True)

# ====================== ESQUEMA PARA CONFIGURACIÓN ======================
class ConfiguracionUsuario(BaseModel):
    notificaciones_email: bool = Field(True, description="Recibir notificaciones por email")
    notificaciones_push: bool = Field(True, description="Recibir notificaciones push")
    moneda_principal: str = Field("CUP", pattern="^(CUP|USD|EUR|MLC)$")
    tema_oscuro: bool = Field(False, description="Usar tema oscuro")
    idioma: str = Field("es", pattern="^(es|en)$")
    zona_horaria: str = Field("America/Havana")

# ====================== ESQUEMA PARA SUBIDA DE ARCHIVOS ======================
class ArchivoSubida(BaseModel):
    nombre: str
    tipo: str
    tamaño_bytes: int
    transacciones_procesadas: int
    transacciones_importadas: int
    fecha_procesamiento: datetime
    
    model_config = ConfigDict(from_attributes=True)

# ====================== ESQUEMA PARA TARIFAS/COMISIONES ======================
class TarifaTransaccion(BaseModel):
    id: int
    banco: str
    tipo_transaccion: TipoTransaccion
    monto_minimo: float
    monto_maximo: float
    tarifa_fija: float
    tarifa_porcentaje: float
    moneda: str
    fecha_vigencia: datetime
    
    model_config = ConfigDict(from_attributes=True)

# ====================== ESQUEMA PARA PLANTILLAS ======================
class PlantillaTransaccion(BaseModel):
    id: int
    nombre: str
    descripcion: str
    banco: str
    beneficiario: Optional[str]
    monto: Optional[float]
    moneda: str
    tipo: TipoTransaccion
    etiquetas: List[str]
    usuario_id: int
    
    model_config = ConfigDict(from_attributes=True)
    
# schemas.py - Agregar

class OpinionCreate(BaseModel):
    titulo: str = Field(..., min_length=3, max_length=100)
    mensaje: str = Field(..., min_length=10, max_length=1000)
    puntuacion: int = Field(5, ge=1, le=5)

class OpinionResponse(BaseModel):
    id: int
    usuario_nombre: str
    titulo: str
    mensaje: str
    puntuacion: int
    fecha: datetime
    
    model_config = ConfigDict(from_attributes=True)