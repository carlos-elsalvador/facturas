import pytesseract
from pdf2image import convert_from_path
import cv2
import numpy as np
import re

# Ruta del PDF
archivo_pdf = "/home/carlos/workbenchPython/mercadona/datos/2025/5_MAYO/MERCADONA_ 20250523-1.pdf"

# Convertir PDF en imágenes
imagen = convert_from_path(archivo_pdf)

def procesar_linea(linea):
    """ Extrae cantidad, descripción y precio de una línea de texto. """
    match = re.match(r"(\d+)\s+([A-ZÑÁÉÍÓÚa-zñáéíóú\s\/-]+)\s+(\d+,\d+)?", linea)

    if match:
        cantidad = int(match.group(1))
        descripcion = match.group(2).strip()
        precio = float(match.group(3).replace(",", ".")) if match.group(3) else None
        return cantidad, descripcion, precio
    
    return None, None, None

def extraer_texto(imagenes):
    """ Extrae texto de una lista de imágenes usando OCR """
    texto_total = ""
    precios_total = []
    
    for imagen in imagenes:
        imagen_cv2 = np.array(imagen)
        imagen_gray = cv2.cvtColor(imagen_cv2, cv2.COLOR_BGR2GRAY)

        texto_total += pytesseract.image_to_string(imagen_gray, lang="spa", config="--psm 4 --oem 3") + "\n"
        texto_precio = pytesseract.image_to_string(imagen_gray, lang="spa", config="--psm 6 -c tessedit_char_whitelist=0123456789,.")
        precios_total.extend(re.findall(r"\b\d+,\d{2}\b", texto_precio))

    return texto_total, precios_total

# Proceso ETL
productos_extraidos = []

# **ETAPA DE EXTRACCIÓN**
texto_extraido, precios_extraidos = extraer_texto(imagen)

# **ETAPA DE TRANSFORMACIÓN**
lineas = texto_extraido.split("\n")

for j, linea in enumerate(lineas):
    cantidad, descripcion, precio = procesar_linea(linea)

    if cantidad and descripcion:
        # Asignar precio desde columna recortada
        if j < len(precios_extraidos):
            precio = float(precios_extraidos[j].replace(",", "."))
        productos_extraidos.append({"cantidad": cantidad, "descripcion": descripcion, "precio": precio})

# **ETAPA DE CARGA: Mostrar resultados**
print("\nProductos extraídos con ETL:")
for producto in productos_extraidos:
    print(producto)

# Resumen de detección
articulos_detectados = len(productos_extraidos)
articulos_con_precio = sum(1 for producto in productos_extraidos if producto["precio"] is not None)
porcentaje_detectados = (articulos_detectados / 39) * 100
porcentaje_con_precio = (articulos_con_precio / articulos_detectados) * 100

print("\n📊 Resumen del proceso ETL 📊")
print(f"🔹 Artículos en la factura: 39")
print(f"✅ Artículos detectados: {articulos_detectados} ({porcentaje_detectados:.2f}%)")
print(f"💰 Con precio detectado: {articulos_con_precio} ({porcentaje_con_precio:.2f}%)")
print(f"⚠️ Artículos sin precio: {articulos_detectados - articulos_con_precio}")
