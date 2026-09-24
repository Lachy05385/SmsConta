import re
from typing import Dict, Any
from datetime import datetime
import unicodedata
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def limpiar_texto(texto: str) -> str:
    """Limpia el texto eliminando espacios extras y normalizando"""
    print("="*60)
    print("📥 TEXTO ORIGINAL:")
    print(texto)
    
    if not texto:
        return ""
    
    # Reemplazar tabulaciones y múltiples espacios por un solo espacio
    texto = re.sub(r'\s+', ' ', texto)
    print("\n📌 Después de quitar tabulaciones:")
    print(texto)
    
    # Eliminar espacios al inicio y final
    texto = texto.strip()
    print("\n📌 Texto limpio final:")
    print(texto)
    print("="*60)
    if texto.startswith("El Titular"):
        return ""
    else:
        return texto

def normalizar_fecha(fecha_str: str) -> str:
    print("recibido para normalizacion como ",fecha_str)
    """
    Normaliza cualquier formato de fecha a DD/MM/YYYY
    CORREGIDA: Ya no invierte día y mes incorrectamente
    """
    from datetime import datetime
    import re
    
    if not fecha_str:
        return datetime.now().strftime("%d/%m/%Y")
    
    print(f"🔄 Normalizando fecha: '{fecha_str}'")
    
    # Extraer todos los números
    numeros = re.findall(r'\d+', fecha_str)
    print(f"   Números encontrados: {numeros}")
    
    if len(numeros) >= 3:
        num1, num2, num3 = numeros[:3]
        
        # Convertir a enteros
        val1, val2, val3 = int(num1), int(num2), int(num3)
        
        
        # Caso 1: Formato YYYY-MM-DD (año primero)
        if val1 > 31:  # El primer número es >31, es el año
            año, mes, dia = val1, val2, val3
            print(f"   Formato YYYY-MM-DD detectado")
        else:
            # Para formatos con día y mes, mantener el orden original
            # NO invertir, confiar en que el texto original tiene el formato correcto
            dia, mes, año = val1, val2, val3
            print(f"   Manteniendo orden original: día={dia}, mes={mes}, año={año}")
        
       
        
        # Formatear con dos dígitos
        
            dia_str = f"{dia:02d}"
            mes_str = f"{mes:02d}"
            año_str = str(año)
      
      
        fecha_normalizada = f"{dia_str}/{mes_str}/{año_str}"
        print(f"✅ Fecha normalizada: {fecha_normalizada}")
        return fecha_normalizada
    
    # Si no se encontraron suficientes números, devolver fecha actual
    return datetime.now().strftime("%d/%m/%Y")

def normalizar_texto_transferencia(texto_crudo: str) -> str:
    """Normaliza el texto eliminando espacios extras y tabs"""
    if not texto_crudo:
        return ""
    
    # Reemplazar tabs y múltiples espacios por un solo espacio
    texto = re.sub(r'\s+', ' ', texto_crudo)
    # Eliminar espacios al inicio y final
    texto = texto.strip()
    
    return texto

def parse_transaccion_texto(texto: str) -> dict:
    """
    Parsea texto de transacción bancaria y extrae los datos
    Versión única y mejorada
    """
    resultado = {
        "banco": "",
        "fecha": "",
        "beneficiario": "",
        "ordenante": "",
        "monto": 0.0,
        "moneda": "CUP",  # Por defecto CUP para bancos cubanos
        "numero_transaccion": "",
        "concepto": ""
    }
        
    # Normalizar texto primero
    texto = normalizar_texto_transferencia(texto)
    print(f"📝 Texto a parsear: {texto}")
    
    # Texto en minúsculas para búsquedas
    texto_lower = texto.lower()
    
    #identificar el mensaje para decidir metodo de proceso
    #transferecnias standares
    patron_movil = r'titular\s+del\s+telefono.*a\s+la\s+cuenta'
    patron_bancaria = r'Beneficiario:.*Ordenante:'
    
    patron_plinea = r'^(?!.*ordenante).*Id Compra:.*$'
    patron_enzona = r'^*Id Compra:.*$'
    patron_transferencia_std1 = re.search(patron_movil, texto, re.IGNORECASE)
    patron_transferencia_std2 = re.search(patron_bancaria, texto, re.IGNORECASE)
    
    #DETECTAR PATRON SIN ORDENANTE "Se ha realizado una ....."
    patron_sin_odenante = r'Se ha realizado una transferencia a la cuenta \d+ de [\d.]+ [A-Z]{3}\. Nro\.?\s*Transaccion [A-Za-z0-9]+\. Fecha: [\d/]+\.'
    
    #patron = r'cuenta\s+(\d+).*?de\s+([0-9.]+)\s*([A-Z]{3}).*?Nro\.?\s*Transaccion\s+([A-Za-z0-9]+).*?Fecha:\s*([0-9/]+)'
    
    

    
    
    if bool(re.search(patron_plinea, texto, re.IGNORECASE | re.DOTALL)):
        resultado = procesar_mensaje_plinea(texto)
        return resultado
    elif texto.startswith("ENZ"):
        print("Procesando ENZONA")
        resultado = procesar_mensaje_enzona_avanzado(texto)
        return resultado
    elif patron_transferencia_std1 or patron_transferencia_std2:
    
        # 1. Buscar BANCO
        bancos = ["banco popular", "bpopular", "popular", "banco metropolitano", "bmetropolitano", 
                "banco nacional", "bancario", "banco"]
        for banco in bancos:
            if banco in texto_lower:
                # Extraer el nombre completo del banco
                match = re.search(r'(banco[^:.]*)[:. ]', texto_lower, re.IGNORECASE)
                if match:
                    resultado["banco"] = match.group(1).strip().title()
                else:
                    resultado["banco"] = "Banco Popular"
                break
        
        # 2. Buscar FECHA - PRIMERO buscar específicamente después de "Fecha:"
        fecha_patterns = [
            r'fecha[:\s]*(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})',  # Fecha: 14/3/2026
            r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})',               # 14/3/2026
        # r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2})',               # 14/3/26
        ]
        
        for pattern in fecha_patterns:
            fecha_match = re.search(pattern, texto, re.IGNORECASE)
            if fecha_match:
                grupos = fecha_match.groups()
                if len(grupos) == 3:
                    # Extraer fecha raw
                    fecha_raw = f"{grupos[0]}/{grupos[1]}/{grupos[2]}"
                    print(f"📅 Fecha raw encontrada: {fecha_raw}")
                    try:
                        resultado["fecha"] = normalizar_fecha(fecha_raw)
                    except Exception as e:
                        print(f"⚠️ Error normalizando fecha: {e}")
                        # Si falla la normalización, usar la fecha raw
                        resultado["fecha"] = fecha_raw
                    break
        
        # 3. Buscar BENEFICIARIO
        beneficiario_patterns = [
            r'beneficiario[:\s]*(\S+)',
            r'beneficiario[:\s]*([0-9*X]+)',
            r'a[:\s]*(\S+)',
            r'para[:\s]*(\S+)',
            r'destino[:\s]*(\S+)',
        ]
        
        for pattern in beneficiario_patterns:
            ben_match = re.search(pattern, texto, re.IGNORECASE)
            if ben_match and len(ben_match.group(1).strip())>4:
                resultado["beneficiario"] = ben_match.group(1).strip()
                print(f"👤 Beneficiario: {resultado['beneficiario']}")
                
        # 4. Buscar ORDENANTE
        ordenante_patterns = [
            r'ordenante[:\s]*(\S+)',
            r'ordenante[:\s]*([0-9*X]+)',
            r'de[:\s]*(\S+)',
            r'origen[:\s]*(\S+)',
            r'remitente[:\s]*(\S+)',
        ]
        
        for pattern in ordenante_patterns:
            ord_match = re.search(pattern, texto, re.IGNORECASE)
            if ord_match:
                resultado["ordenante"] = ord_match.group(1).strip()
                print(f"👤 Ordenante: {resultado['ordenante']}")
                break
            
        print("ATENCION------")
        print(resultado["beneficiario"])
        # caso no hay beneficiario

        if not resultado["beneficiario"]:
            print("Buscando Beneficiario ")
            resultado["beneficiario"] = buscarBeneficiario_y_telefono(texto)[1]
            resultado["ordenante"] = f"tel:{buscarBeneficiario_y_telefono(texto)[0]}"


        # CASE BANCO FALTANTE EN TEXTO DE TRASNFERENCIA          
        if not resultado["banco"]:
            print("obtener por numero de cuenta")
            resultado["banco"] = buscarBancoFaltante(resultado["beneficiario"])
            
            
        
        
        # 5. Buscar MONTO y MONEDA
        monto_patterns = [
            r'monto[:\s]*([\d,.]+)\s*([A-Z]{3})',
            r'importe[:\s]*([\d,.]+)\s*([A-Z]{3})',
            r'([\d,.]+)\s*(CUP|USD|EUR|MLC)',
            r'monto[:\s]*([\d,.]+)',
        ]
        
        for pattern in monto_patterns:
            monto_match = re.search(pattern, texto, re.IGNORECASE)
            if monto_match:
                grupos = monto_match.groups()
                if len(grupos) == 2:
                    # Tiene monto y moneda
                    monto_str = grupos[0].replace(',', '')
                    resultado["monto"] = round(float(monto_str), 2)
                    resultado["moneda"] = grupos[1].upper()
                else:
                    # Solo monto
                    monto_str = grupos[0].replace(',', '')
                    resultado["monto"] = round(float(monto_str), 2)
                print(f"💰 Monto: {resultado['monto']} {resultado['moneda']}")
                break
        
        # 6. Buscar NÚMERO DE TRANSACCIÓN
        transaccion_patterns = [
            r'nro\.?\s*transaccion[:\s]*(\S+)',
            r'referencia[:\s]*(\S+)',
            r'operacion[:\s]*(\S+)',
            r'codigo[:\s]*(\S+)',
            r'([A-Z0-9]{8,})',
        ]
        
        for pattern in transaccion_patterns:
            ref_match = re.search(pattern, texto, re.IGNORECASE)
            if ref_match:
                resultado["numero_transaccion"] = ref_match.group(1).strip()
                print(f"🔢 Transacción: {resultado['numero_transaccion']}")
                break
        
        # Si no se encontró número, generar uno
        if not resultado["numero_transaccion"]:
            resultado["numero_transaccion"] = f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}"
            print(f"🆕 Número generado: {resultado['numero_transaccion']}")
        
        # 7. Buscar CONCEPTO
        concepto_match = re.search(r'concepto[:\s]*([^.]+)', texto, re.IGNORECASE)
        if concepto_match:
            resultado["concepto"] = concepto_match.group(1).strip()
        
        # Si no se encontró fecha, usar actual
        if not resultado["fecha"]:
            resultado["fecha"] = datetime.now().strftime("%d/%m/%Y")
            print(f"📅 Fecha actual usada: {resultado['fecha']}")
            
        print(resultado)
        return resultado
    elif texto.startswith("Se ha realizado"):
        resultado = procesar_transferencia_sin_ordenante(texto)
        print("Activando Nueva funcion sin ordenante.... ")
        return resultado
        
    
    
    else:
        print("Mensaje incorrecto")    
        return "Mensaje Incorrecto"

# CON TEXTO SE HA REALIZADO UNA TRASNSFERENCIA 

def procesar_transferencia_sin_ordenante(mensaje):
    """
    Usa una sola expresión regular para extraer todos los datos
    """
    resultado = {
        "banco": "Transferencia",
        "fecha": "",
        "beneficiario": "",
        "ordenante": "****",
        "monto": 0.0,
        "moneda": "CUP",
        "numero_transaccion": "",
        "concepto": "Transferencia recibida"
    }
    
    # Patrón único que captura todos los campos
    patron = r'cuenta\s+(\d+).*?de\s+([0-9.]+)\s*([A-Z]{3}).*?Nro\.?\s*Transaccion\s+([A-Za-z0-9]+).*?Fecha:\s*([0-9/]+)'
    
    match = re.search(patron, mensaje, re.IGNORECASE | re.DOTALL)
    
    if match:
        resultado["beneficiario"] = match.group(1)
        resultado["monto"] = float(match.group(2))
        resultado["moneda"] = match.group(3).upper()
        resultado["numero_transaccion"] = match.group(4)
        resultado["fecha"] = match.group(5)
    
    return resultado
    
    
    
    
def buscarBeneficiario_y_telefono(texto):
    patron = r'telefono\s+(\d+).*?cuenta\s+(\d+)'

# Buscar
    match = re.search(patron, texto, re.IGNORECASE | re.DOTALL)

    if match:
        telefono = match.group(1)
        cuenta = match.group(2)
        #print(f"📱 Teléfono: {telefono}")
        #print(f"💳 Cuenta: {cuenta}")
    else:
        print("No se encontraron coincidencias")
        
    
    return telefono,cuenta
def buscarBancoFaltante(texto):
    
    bpa = ["9205","9206","9238","9212"]
    bandec = ["0689"]
    bancoMetropolitano = ["9227"]
    
    
    if list(filter(lambda x : texto.startswith(x),bpa)):
            texto ="Banco Popular de Ahorro"
    elif list(filter(lambda x : texto.startswith(x),bandec)):
        texto = "Banco de Credito y Comercio..."
    elif list(filter(lambda x : texto.startswith(x),bancoMetropolitano)):
        texto = "Banco Metropilitano..."
    else:
        texto = "Banco Cubano"
        
    return texto

def procesar_mensaje_plinea(mensaje):
    resultado = {
        "banco": "",
        "fecha": "",
        "beneficiario": "",
        "ordenante": "",
        "monto": 0.0,
        "moneda": "CUP",
        "numero_transaccion": "",
        "concepto": ""
    }
    
    # Extraer banco (primeras palabras antes de ":")
    banco_match = re.search(r'^([^:]+):', mensaje)
    if banco_match:
        resultado["banco"] = banco_match.group(1).strip()
    
    # Extraer fecha
    fecha_match = re.search(r'Fecha:\s*([0-9/]+)', mensaje)
    if fecha_match:
        resultado["fecha"] = fecha_match.group(1).strip()
        
    
    
    # Extraer entidad y ponerla en beneficiario (máximo 12 caracteres)
    entidad_match = re.search(r'Entidad:\s*(.{12})', mensaje)
    #entidad_match = re.search(r'\([^)]+\)', mensaje)
    #print("Entidad match -----",entidad_match.group(1).strip())
    #inicio = entidad_match.group(1).strip().find('(')
    #fin = entidad_match.group(1).strip().find(')')
    #print("Entidad match - >",entidad_match)
    if entidad_match:
        entidad = entidad_match.group(1).strip().split()
        
        
        resultado["beneficiario"] = str(entidad)
    
    # Extraer ID de compra y ponerla en ordenante
    id_compra_match = re.search(r'Id Compra:\s*([0-9]+)', mensaje)
    if id_compra_match:
        resultado["ordenante"] = id_compra_match.group(1).strip()
    
    # Extraer importe (solo el primer Importe, no el Importe Pagado)
    importe_match = re.search(r'Importe:\s*([0-9.]+)\s*([A-Z]+)', mensaje)
    if importe_match:
        resultado["monto"] = float(importe_match.group(1))
        resultado["moneda"] = importe_match.group(2)
    
    # Extraer número de transacción
    transaccion_match = re.search(r'(?:Nro|No)\.?\s*Transaccion:\s*([^\n\.]+)', mensaje, re.IGNORECASE)
    if transaccion_match:
        resultado["numero_transaccion"] = transaccion_match.group(1).strip()[:13]
        
        
    print()
    
    return resultado
def obtener_beneficiario_p_linea(texto,i,f):
    entidad = texto[i:f+1]
    
    return entidad[:15]

def ordenar_parseo_de_datos(texto: str):
    
    
    
    
    return "Texto Procesado"

def enmascarar_numero_cuenta(cuenta: str) -> str:
    """Enmascara número de cuenta mostrando solo primeros y últimos dígitos"""
    if not cuenta or len(cuenta) < 8:
        return cuenta
    
    # Limpiar espacios
    cuenta = re.sub(r'\s+', '', cuenta)
    
    # Mostrar primeros 4 y últimos 4
    if len(cuenta) > 8:
        return cuenta[:4] + "*" * (len(cuenta) - 8) + cuenta[-4:]
    return cuenta

# Mantener compatibilidad
limpiar_texto_original = limpiar_texto

def procesar_mensaje_enzona_avanzado(mensaje):
    resultado = {
        "banco": "",
        "fecha": "",
        "beneficiario": "",
        "ordenante": "",
        "monto": 0.0,
        "moneda": "CUP",
        "numero_transaccion": "",
        "concepto": ""
    }
    
    # Extraer banco
    banco_match = re.search(r'^(ENZONA)', mensaje, re.IGNORECASE)
    if banco_match:
        resultado["banco"] = banco_match.group(1).upper()
    
    # Extraer importe y moneda
    # Patrones posibles: "Importe: 131.00 CUP" o "Importe:6000.00 CUP"
    importe_match = re.search(r'Importe:\s*([0-9]+\.?[0-9]*)\s*([A-Z]{3})', mensaje, re.IGNORECASE)
    if importe_match:
        resultado["monto"] = float(importe_match.group(1))
        resultado["moneda"] = importe_match.group(2).upper()
    
    # Extraer número de transacción (más flexible)
    # Patrones posibles: "No.: 3AAyFSEr5zCP" o "No.: btW3BGhGpnEH"
    transaccion_match = re.search(r'No\.:\s*([A-Za-z0-9]+)', mensaje)
    if transaccion_match:
        resultado["numero_transaccion"] = transaccion_match.group(1)
    
    # Extraer tipo de operación y asignar a concepto
    tipo_match = re.search(r'ENZONA\s+(pago recibido|transferencia recibida)', mensaje, re.IGNORECASE)
    if tipo_match:
        tipo = tipo_match.group(1).lower()
        if tipo == "pago recibido":
            resultado["concepto"] = "Pago recibido"
        elif tipo == "transferencia recibida":
            resultado["concepto"] = "Transferencia recibida"
    
    # Asignar máscara a campos faltantes
    resultado["fecha"] = get_Fecha_inexistente()
    resultado["beneficiario"] = "xxxx-xxxx-xxxx-xxxx"
    resultado["ordenante"] = "xxxx-xxxx-xxxx-xxxx"
    
    return resultado

def get_Fecha_inexistente():
    fecha_actual = datetime.now()
    fecha_formateada = fecha_actual.strftime("%d/%m/%Y")
    
    return fecha_formateada 

# Extaer desde imagen 

import pytesseract
from PIL import Image
import io
import re

# Configurar ruta de Tesseract (ajusta según tu instalación)
# Windows: pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# Linux/Mac: generalmente ya está en el PATH

def extraer_texto_de_imagen(imagen_bytes: bytes) -> str:
    """
    Extrae texto de una imagen usando OCR (Tesseract)
    Versión mejorada para capturas de pantalla de transferencias
    """
    try:
        print("📸 Abriendo imagen desde bytes...")
        imagen = Image.open(io.BytesIO(imagen_bytes))
        
        # Mejorar calidad para OCR
        # 1. Convertir a escala de grises
        if imagen.mode != 'RGB':
            imagen = imagen.convert('RGB')
        imagen_gris = imagen.convert('L')
        
        # 2. Aumentar contraste
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Contrast(imagen_gris)
        imagen_mejorada = enhancer.enhance(2.5)
        
        # 3. Binarizar (convertir a blanco y negro)
        imagen_binaria = imagen_mejorada.point(lambda x: 0 if x < 128 else 255, '1')
        
        # 4. Redimensionar para mejorar OCR (si es muy pequeña)
        if imagen_binaria.width < 400:
            factor = 2
            new_size = (imagen_binaria.width * factor, imagen_binaria.height * factor)
            imagen_binaria = imagen_binaria.resize(new_size, Image.Resampling.LANCZOS)
        
        print("🔍 Extrayendo texto con OCR (español+inglés)...")
        texto = pytesseract.image_to_string(imagen_binaria, lang='spa+eng')
        
        texto = texto.strip()
        print(f"✅ OCR completado. {len(texto)} caracteres extraídos.")
        
        if len(texto) < 10:
            print("⚠️ Se extrajo muy poco texto. ¿La imagen es legible?")
        
        return texto
        
    except Exception as e:
        print(f"❌ Error en OCR: {e}")
        raise ValueError(f"No se pudo extraer texto de la imagen: {e}")

import re
import unicodedata

def limpiar_texto_ocr(texto_ocr: str) -> str:
    """
    Limpia y normaliza texto extraído por OCR que puede tener errores
    """
    # Eliminar caracteres no deseados
    texto = re.sub(r'[^\w\sáéíóúñÁÉÍÓÚÑ:./\-]', ' ', texto_ocr)
    
    # Reemplazar múltiples espacios por uno solo
    texto = re.sub(r'\s+', ' ', texto)
    
    # Eliminar espacios al inicio y final
    texto = texto.strip()
    
    # Normalizar mayúsculas/minúsculas para palabras clave
    texto_lower = texto.lower()
    
    return texto, texto_lower

def extraer_monto_ocr(texto: str, texto_lower: str) -> tuple:
    """
    Extrae monto de texto OCR con patrones más flexibles
    """
    # Patrones más flexibles para montos
    patrones = [
        r'monto[:\s]*([\d,.]+)',           # monto: 240.00
        r'pets[:\s]*([\d,.]+)',             # pets: 240.00 (de tu texto)
        r'importe[:\s]*([\d,.]+)',          # importe: 240.00
        r'valor[:\s]*([\d,.]+)',            # valor: 240.00
        r'([\d,.]+)\s*(cup|usd|eur|mlc)',   # 240.00 cup
        r'(\d+[.,]\d{2})\s*$',              # 240.00 al final
        r'(\d+[.,]\d{2})',                  # cualquier número con decimales
    ]
    
    for patron in patrones:
        match = re.search(patron, texto_lower, re.IGNORECASE)
        if match:
            monto_str = match.group(1).replace(',', '').replace('.', '')
            if monto_str.isdigit():
                monto = float(monto_str) / 100 if '.' in match.group(1) else float(monto_str)
                return round(monto, 2)
    
    # Buscar cualquier número que parezca un monto (2 decimales)
    numeros = re.findall(r'(\d+[.,]\d{2})', texto)
    if numeros:
        ultimo = numeros[-1]
        return float(ultimo.replace(',', '.'))
    
    return 0.0

def extraer_telefono_ocr(texto: str) -> str:
    """
    Extrae número de teléfono de texto OCR (formato cubano: 5 seguido de 7 dígitos)
    """
    # Patrones para teléfonos cubanos
    patrones = [
        r'(5\d{7})',                        # 5354882197
        r'(\d{3}\s*\d{3}\s*\d{4})',         # 535 488 2197
        r'tel[.:]?\s*(\d{7,})',             # tel: 5354882197
        r'telefono[.:]?\s*(\d{7,})',        # telefono: 5354882197
    ]
    
    for patron in patrones:
        match = re.search(patron, texto)
        if match:
            telefono = re.sub(r'\s+', '', match.group(1))
            return telefono
    
    return ""

def extraer_cuenta_ocr(texto: str) -> str:
    """
    Extrae número de cuenta de texto OCR
    """
    # Patrones para cuentas (13 dígitos o 10+ dígitos)
    patrones = [
        r'cuenta[:\s]*(\d{10,})',
        r'beneficiario[:\s]*(\d{10,})',
        r'(\d{13})',                        # 13 dígitos seguidos
        r'(\d{10,})',                       # 10+ dígitos
    ]
    
    for patron in patrones:
        match = re.search(patron, texto)
        if match:
            cuenta = match.group(1)
            if len(cuenta) >= 10:
                return cuenta
    
    return ""

def extraer_numero_transaccion_ocr(texto: str) -> str:
    """
    Extrae número de transacción de texto OCR
    """
    patrones = [
        r'id compra[:\s]*([A-Z0-9]+)',      # Id Compra: 3339/00396
        r'nro[.:]?\s*transaccion[:\s]*([A-Z0-9]+)',
        r'referencia[:\s]*([A-Z0-9]+)',
        r'operacion[:\s]*([A-Z0-9]+)',
        r'([A-Z0-9]{8,})',                  # cualquier código de 8+ caracteres
    ]
    
    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return "xxxxxxx"

def extraer_entidad_ocr(texto: str, texto_lower: str) -> str:
    """
    Extrae el nombre de la entidad/ordenante
    """
    # Buscar después de "Entidad:"
    entidad_match = re.search(r'entidad[:\s]*([^:\n]+)', texto, re.IGNORECASE)
    if entidad_match:
        nombre = entidad_match.group(1).strip()
        # Limpiar caracteres extraños
        nombre = re.sub(r'[\(\)]', '', nombre)
        if len(nombre) > 3:
            return nombre
    
    # Buscar después de "Lazaro" o similar (nombre del usuario)
    nombre_match = re.search(r'(Lazaro\s+[A-Za-z]+)', texto, re.IGNORECASE)
    if nombre_match:
        return nombre_match.group(1).strip()
    
    return ""

def extraer_fecha_ocr(texto: str) -> str:
    """
    Extrae fecha de texto OCR (corrige errores comunes como "E Z/ 2026")
    """
    # Primero, intentar con patrones estándar
    patrones = [
        r'fecha[:\s]*(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})',
        r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})',
        r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2})',
    ]
    
    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            grupos = match.groups()
            if len(grupos) == 3:
                dia, mes, año = grupos
                return normalizar_fecha(f"{dia}/{mes}/{año}")
    
    # Si no se encontró, buscar patrones con espacios como "E Z/ 2026"
    # Esto es común en OCR cuando "31" se lee como "E Z"
    fecha_corregida = re.sub(r'[A-Za-z]', '', texto)
    match = re.search(r'(\d{1,2})\s*(\d{1,2})\s*(\d{4})', fecha_corregida)
    if match:
        dia, mes, año = match.groups()
        if int(dia) <= 31 and int(mes) <= 12:
            return normalizar_fecha(f"{dia}/{mes}/{año}")
    
    from datetime import datetime
    return datetime.now().strftime("%d/%m/%Y")

def extraer_datos_transferencia_de_texto_ocr(texto_ocr: str) -> dict:
    """
    Versión especializada para extraer datos de texto OCR con errores.
    Retorna siempre un diccionario con campos, usando valores por defecto.
    """
    resultado = {
        "banco": "Banco cubano",          # 👈 valor por defecto
        "fecha": "",                      # se pondrá la actual si no se encuentra
        "beneficiario": "XXXX",
        "ordenante": "XXXX",
        "telefono_ordenante": "",
        "monto": 0.0,
        "moneda": "CUP",
        "numero_transaccion": "",
        "concepto": ""
    }
    
    # Limpiar texto OCR
    texto, texto_lower = limpiar_texto_ocr(texto_ocr)
    print(f"📝 Texto OCR limpiado: {texto}")
    
    # 1. Extraer NÚMERO DE TRANSACCIÓN (prioritario)
    nro = extraer_numero_transaccion_ocr(texto)
    if nro and len(nro) >= 4:
        resultado["numero_transaccion"] = nro
        print(f"🔢 Número de transacción: {resultado['numero_transaccion']}")
    
    # 2. Extraer MONTO (prioritario)
    monto = extraer_monto_ocr(texto, texto_lower)
    if monto > 0:
        resultado["monto"] = monto
        print(f"💰 Monto: {resultado['monto']}")
    
    # 3. Extraer FECHA (si no, se usará la actual más adelante)
    fecha = extraer_fecha_ocr(texto)
    if fecha:
        resultado["fecha"] = fecha
        print(f"📅 Fecha: {resultado['fecha']}")
    
    # 4. Extraer BANCO (si no, ya tenemos "Banco cubano")
    bancos = ["banco popular", "bpopular", "popular", "banco metropolitano", "bmetropolitano", "banco nacional"]
    for banco in bancos:
        if banco in texto_lower:
            resultado["banco"] = "Banco Popular de Ahorro"  # o el que corresponda
            break
    
  
    
    
    # 3. Extraer ORDENANTE (entidad que envía)
    beneficiario = extraer_entidad_ocr(texto, texto_lower)
    if beneficiario:
        resultado["beneficiario"] = beneficiario
    
    # 4. Extraer TELÉFONO
    telefono = extraer_telefono_ocr(texto)
    if telefono:
        resultado["telefono_ordenante"] = telefono
        if not resultado["ordenante"]:
            resultado["ordenante"] = f"tel:{telefono}"
    
    # 5. Extraer CUENTA BENEFICIARIO
    cuenta = extraer_cuenta_ocr(texto)
    if cuenta:
        resultado["beneficiario"] = cuenta #cmnbie a ordenente
    
    # 6. Extraer MONTO
    monto = extraer_monto_ocr(texto, texto_lower)
    if monto > 0:
        resultado["monto"] = monto
    
    # 7. Extraer NÚMERO DE TRANSACCIÓN
    nro = extraer_numero_transaccion_ocr(texto)
    if nro:
        resultado["numero_transaccion"] = nro
    
    # 8. Extraer CONCEPTO (lo que dice después de "Pago completado" o similar)
    concepto_match = re.search(r'pago\s+completado[.:]?\s*(.*?)(?=entidad|id compra|$)', texto_lower, re.IGNORECASE)
    if concepto_match:
        resultado["concepto"] = concepto_match.group(1).strip()[:100]
    
    # 9. Limpiar número de transacción
    if resultado["numero_transaccion"] or len(resultado["numero_transaccion"]) < 4: #and "ELIMINAR" in resultado["numero_transaccion"].upper():
        # Buscar otro código más abajo
        otro_codigo = re.search(r'(\d{4}/\d{5})', texto)
        print(otro_codigo)
        if otro_codigo:
            resultado["numero_transaccion"] = otro_codigo.group(1)
    print("Numero de transaccion XX = ",resultado["numero_transaccion"])
    # Asignar valores por defecto si faltan
    if not resultado["beneficiario"]:
        resultado["beneficiario"] = "XXXX-xxxx-xxxx-XXXX"
    
    if not resultado["ordenante"]:
        resultado["ordenante"] = "XXXX-xxxx-xxxx-XXXX"
    
   
    
    return resultado

# utils.py - Agregar esta función

def validar_y_normalizar_datos_transferencia(datos: dict) -> dict:
    """
    Valida y normaliza los datos de una transferencia ANTES de guardar.
    Asegura que todos los campos requeridos tengan valores válidos.
    """
    from datetime import datetime
    
    # 1. Validar MONTO (debe ser > 0)
    if datos.get("monto", 0) <= 0:
        print(f"⚠️ Monto inválido ({datos.get('monto')}), usando valor por defecto 1.00")
        datos["monto"] = 1.00  # Valor mínimo válido
    
    # 2. Validar FECHA
    if not datos.get("fecha"):
        datos["fecha"] = datetime.now().strftime("%d/%m/%Y")
    else:
        try:
            datos["fecha"] = normalizar_fecha(datos["fecha"])
        except:
            datos["fecha"] = datetime.now().strftime("%d/%m/%Y")
    
    # 3. Validar BANCO (mínimo 2 caracteres)
    if not datos.get("banco") or len(datos["banco"]) < 2:
        datos["banco"] = "Banco no especificado"
    
    # 4. Validar BENEFICIARIO (mínimo 4 caracteres)
    if not datos.get("beneficiario") or len(datos["beneficiario"]) < 4:
        datos["beneficiario"] = "XXXX"
    
    # 5. Validar ORDENANTE (mínimo 4 caracteres)
    if not datos.get("ordenante") or len(datos["ordenante"]) < 4:
        if datos.get("telefono_ordenante"):
            datos["ordenante"] = f"tel:{datos['telefono_ordenante']}"
        else:
            datos["ordenante"] = "XXXX"
    
    # 6. Validar NÚMERO DE TRANSACCIÓN (mínimo 4 caracteres)
    if not datos.get("numero_transaccion") or len(datos["numero_transaccion"]) < 4:
        datos["numero_transaccion"] = f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # 7. Validar MONEDA
    monedas_validas = ['CUP', 'USD', 'EUR', 'MLC']
    moneda = datos.get("moneda", "CUP").upper()
    if moneda not in monedas_validas:
        datos["moneda"] = "CUP"
    else:
        datos["moneda"] = moneda
    
    return datos

import socket
#mport requests

def obtener_server_ip():
    """
    Obtiene la dirección IP local de la PC en la red local
    """
    try:
        # Crear un socket para obtener la IP local
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_local = s.getsockname()[0]
        s.close()
        return ip_local
    except Exception:
        return "127.0.0.1"  # Fallback a localhost

def obtener_ip_publica():
    """
    Obtiene la IP pública (para acceso desde internet, opcional)
    """
    try:
        response = requests.get('https://api.ipify.org', timeout=5)
        return response.text
    except Exception:
        return "No disponible"
    

#limpiar datos en restauracion CSV
def parse_csv_value(valor, tipo):
    if valor == '' or valor is None:
        return None if tipo in ['datetime'] else (0 if tipo in ['int','float'] else '')
    if tipo == 'int':
        return int(valor)
    if tipo == 'float':
        return float(valor)
    if tipo == 'datetime':
        return datetime.fromisoformat(valor)
    return valor
    

def get_server_url(port=8000):
    """
    Retorna la URL completa del servidor
    """
    ip = obtener_server_ip()
    return f"http://{ip}:{port}"