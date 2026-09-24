# app/database.py
import os
import sys
import requests
import json
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import sqlalchemy.pool as pool

# 🔧 PARCHE RADICAL: Eliminar el listener regexp de SQLAlchemy
from sqlalchemy.dialects.sqlite import pysqlite
from sqlalchemy.event import remove

# 1. Eliminar el listener existente
try:
    from sqlalchemy.dialects.sqlite.base import _regexp_listener
    if hasattr(pysqlite.SQLiteDialect_pysqlite, '_regexp_listener'):
        remove(pysqlite.SQLiteDialect_pysqlite, 'connect', _regexp_listener)
        print("✅ Listener regexp eliminado")
except:
    pass

# 2. Sobrescribir el método set_regexp con una función vacía
def dummy_set_regexp(self, dbapi_connection):
    """No hace nada, evita el error."""
    pass

pysqlite.SQLiteDialect_pysqlite.set_regexp = dummy_set_regexp

# 3. Deshabilitar el listener en la clase
pysqlite.SQLiteDialect_pysqlite._regexp_listener = None

# 🔧 PARCHE PARA EL NIVEL DE AISLAMIENTO
# Sobrescribir el método get_isolation_level para que devuelva un valor válido
original_get_isolation_level = pysqlite.SQLiteDialect_pysqlite.get_isolation_level

def patched_get_isolation_level(self, dbapi_conn):
    """Devuelve un nivel de aislamiento válido para Turso."""
    try:
        # Intentar obtener el nivel real
        result = original_get_isolation_level(self, dbapi_conn)
        if result is not None:
            return result
    except:
        pass
    # Si falla o devuelve 0, usar el nivel por defecto
    return "READ UNCOMMITTED"

pysqlite.SQLiteDialect_pysqlite.get_isolation_level = patched_get_isolation_level

# Detectar entorno
IS_PRODUCTION = os.getenv("RENDER", "false").lower() == "true"

if IS_PRODUCTION:
    TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
    TURSO_TOKEN = os.getenv("TURSO_TOKEN")
    
    if not TURSO_DATABASE_URL or not TURSO_TOKEN:
        raise ValueError("❌ Variables TURSO_DATABASE_URL y TURSO_TOKEN son obligatorias en Render")
    
    class TursoConnection:
        """Wrapper completo para Turso compatible con SQLAlchemy."""
        def __init__(self):
            self.headers = {
                "Authorization": f"Bearer {TURSO_TOKEN}",
                "Content-Type": "application/json"
            }
            self.url = TURSO_DATABASE_URL.replace("libsql://", "https://")
            self.closed = False
            self.transaction_active = False
            self._callbacks = []
            # Para el nivel de aislamiento
            self.isolation_level = "READ UNCOMMITTED"
        
        def cursor(self):
            return TursoCursor(self)
        
        def execute(self, sql, parameters=None):
            cursor = self.cursor()
            cursor.execute(sql, parameters)
            return cursor
        
        def commit(self):
            self.transaction_active = False
            return self
        
        def rollback(self):
            self.transaction_active = False
            return self
        
        def close(self):
            self.closed = True
        
        # ⚠️ MÉTODOS REQUERIDOS POR SQLALCHEMY
        def create_function(self, name, num_args, func, *, deterministic=False):
            """Simula create_function para evitar errores."""
            pass
        
        def create_aggregate(self, name, num_args, aggregate):
            """Simula create_aggregate para evitar errores."""
            pass
        
        def create_collation(self, name, collation):
            """Simula create_collation para evitar errores."""
            pass
        
        def set_authorizer(self, authorizer):
            """Simula set_authorizer para evitar errores."""
            pass
        
        def set_progress_handler(self, handler, n):
            """Simula set_progress_handler para evitar errores."""
            pass
        
        def set_trace_callback(self, callback):
            """Simula set_trace_callback para evitar errores."""
            pass
        
        def __enter__(self):
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            self.close()
    
    class TursoCursor:
        def __init__(self, connection):
            self.connection = connection
            self.arraysize = 1
            self._results = []
            self._rowcount = -1
            self._lastrowid = None
            self._description = None
            self.closed = False
        
        def execute(self, sql, parameters=None):
            if self.closed:
                raise Exception("Cursor already closed")
            
            payload = {"requests": [{"type": "execute", "stmt": {"sql": sql}}]}
            
            if parameters:
                args = []
                if isinstance(parameters, dict):
                    for key, value in parameters.items():
                        args.append(self._convert_param(value))
                elif isinstance(parameters, (list, tuple)):
                    for value in parameters:
                        args.append(self._convert_param(value))
                else:
                    args.append(self._convert_param(parameters))
                
                if args:
                    payload["requests"][0]["stmt"]["args"] = args
            
            try:
                response = requests.post(
                    f"{self.connection.url}/v2/pipeline",
                    headers=self.connection.headers,
                    json=payload,
                    timeout=60
                )
                
                if response.status_code != 200:
                    raise Exception(f"Error en Turso: {response.status_code} - {response.text}")
                
                data = response.json()
                self._results = []
                self._rowcount = 0
                self._description = None
                
                if "results" in data and data["results"]:
                    result = data["results"][0]
                    if "response" in result and "result" in result["response"]:
                        result_data = result["response"]["result"]
                        
                        if "cols" in result_data:
                            self._description = [
                                (col.get("name"), None, None, None, None, None, None)
                                for col in result_data["cols"]
                            ]
                        
                        rows = result_data.get("rows", [])
                        for row in rows:
                            row_values = []
                            for col in row:
                                row_values.append(col.get("value"))
                            self._results.append(tuple(row_values))
                        
                        self._rowcount = len(self._results)
                        
                        if "last_insert_rowid" in result_data:
                            self._lastrowid = result_data["last_insert_rowid"]
                
                return self
                
            except requests.exceptions.Timeout:
                raise Exception("Timeout conectando a Turso")
            except Exception as e:
                raise Exception(f"Error en ejecución: {str(e)}")
        
        def _convert_param(self, value):
            if value is None:
                return {"type": "null", "value": None}
            elif isinstance(value, bool):
                return {"type": "integer", "value": "1" if value else "0"}
            elif isinstance(value, int):
                return {"type": "integer", "value": str(value)}
            elif isinstance(value, float):
                return {"type": "text", "value": str(value)}
            else:
                return {"type": "text", "value": str(value)}
        
        def fetchone(self):
            if self._results:
                return self._results.pop(0)
            return None
        
        def fetchall(self):
            return self._results
        
        def fetchmany(self, size=None):
            if size is None:
                size = self.arraysize
            if self._results:
                result = self._results[:size]
                self._results = self._results[size:]
                return result
            return []
        
        @property
        def rowcount(self):
            return self._rowcount
        
        @property
        def lastrowid(self):
            return self._lastrowid
        
        @property
        def description(self):
            return self._description
        
        def close(self):
            self.closed = True
    
    # Crear el engine con el nivel de aislamiento configurado
    def create_turso_connection():
        return TursoConnection()
    
    # 🔧 Configurar el engine con el nivel de aislamiento
    engine = create_engine(
        "sqlite://",
        creator=create_turso_connection,
        poolclass=pool.StaticPool,
        connect_args={"check_same_thread": False},
        isolation_level="READ UNCOMMITTED"  # 🔑 Forzar el nivel de aislamiento
    )
    
    print("✅ Conectado a Turso en la nube")
    
else:
    # En local: Usar SQLite
    from pathlib import Path
    
    DATA_DIR = Path(__file__).resolve().parent.parent / "data"
    DATA_DIR.mkdir(exist_ok=True)
    
    SQLITE_DATABASE_URL = f"sqlite:///{DATA_DIR}/bancaria.db"
    engine = create_engine(
        SQLITE_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    print("✅ Usando SQLite local para desarrollo")

# Sesión y Base
SessionLocal = sessionmaker(autocommit=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    from app import models
    Base.metadata.create_all(bind=engine)
    print("✅ Tablas creadas correctamente")