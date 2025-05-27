import pytesseract
from pdf2image import convert_from_path
import cv2
import numpy as np
import re
import os
import glob
import pandas as pd

# Ruta base donde están organizadas las facturas
ruta_base = "/home/carlos/workbenchPython/facturas/datos"

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

def extraer_metadatos(texto):
    """ Extrae fecha, establecimiento y total de pago del texto """
    fecha_match = re.search(r"\d{2}/\d{2}/\d{4}", texto)    
    establecimiento_match = re.search(r"\b(?:MERCADONA|CARREFOUR|ALCAMPO|LIDL)\b", texto, re.IGNORECASE)
    total_match = re.search(r"TOTAL\s+(\d+,\d{2})", texto)

    fecha = fecha_match.group(0) if fecha_match else "Desconocida"
    establecimiento = establecimiento_match.group(0) if establecimiento_match else "Desconocido"
    total_pagar = float(total_match.group(1).replace(",", ".")) if total_match else 0.0

    return fecha, establecimiento, total_pagar

# Almacenar productos de todas las facturas
facturas_procesadas = []

for año in os.listdir(ruta_base):
    ruta_año = os.path.join(ruta_base, año)
    if os.path.isdir(ruta_año):
        for mes in os.listdir(ruta_año):
            ruta_mes = os.path.join(ruta_año, mes)

            # Filtrar solo facturas cuyo nombre inicia con "MERCADONA"
            facturas = glob.glob(os.path.join(ruta_mes, "MERCADONA_*.pdf"))
            print(f"📂 Procesando {len(facturas)} facturas de MERCADONA en {mes} {año}")

            for factura in facturas:
                print(f"🔍 Procesando factura: {factura}")
                imagenes = convert_from_path(factura)
                texto_extraido, precios_extraidos = extraer_texto(imagenes)
                fecha, establecimiento, total_pagar = extraer_metadatos(texto_extraido)

                productos_extraidos = []
                lineas = texto_extraido.split("\n")

                for j, linea in enumerate(lineas):
                    cantidad, descripcion, precio = procesar_linea(linea)

                    if cantidad and descripcion:
                        if j < len(precios_extraidos):
                            precio = float(precios_extraidos[j].replace(",", "."))
                        productos_extraidos.append({
                            "cantidad": cantidad, 
                            "descripcion": descripcion, 
                            "precio": precio, 
                            "fecha": fecha, 
                            "establecimiento": establecimiento, 
                            "total_pagar": total_pagar
                        })                        
                
                # Agregar datos a cada factura procesada
                facturas_procesadas.extend(productos_extraidos)

                # Agregar los nuevos campos a la factura
                for producto in productos_extraidos:
                    producto["articulos_detectados"] = len(productos_extraidos)
                    producto["precios_detectados"] = sum(1 for p in productos_extraidos if p["precio"] is not None)

# Crear DataFrame y guardar en CSV
df_facturas = pd.DataFrame(facturas_procesadas)
df_facturas.to_csv("facturas_supermercado.csv", index=False, encoding="utf-8")

print("📂 Archivo CSV generado: facturas_supermercado.csv")
print(df_facturas.head())
