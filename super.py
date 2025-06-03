import pytesseract
from pdf2image import convert_from_path
import cv2
import numpy as np
import re
import os
import glob
import pandas as pd
from datetime import datetime
from my_mysql  import * # Importamos nuestro archivo de gestión de MySQL

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

    # **CORRECCIÓN** Convierte la fecha al formato correcto antes de retornar
    if fecha != "Desconocida":
        try:
            fecha = datetime.strptime(fecha, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            fecha = "Fecha Inválida"    

    return fecha, establecimiento, total_pagar

def procesar_linea(linea):
    """ Extrae cantidad, descripción y precio de una línea de texto """
    match = re.match(r"(\d+)\s+([A-ZÑÁÉÍÓÚa-zñáéíóú\s\/-]+)\s+(\d+,\d+)?", linea)
    
    if match:
        cantidad = int(match.group(1))
        descripcion = match.group(2).strip()
        precio = float(match.group(3).replace(",", ".")) if match.group(3) else None
        return cantidad, descripcion, precio
    
    return None, None, None

def listar_facturas():
    """Lista todas las facturas en las carpetas organizadas por año y mes"""
    facturas_en_carpetas = []
    
    for año in os.listdir(ruta_base):
        ruta_año = os.path.join(ruta_base, año)
        if os.path.isdir(ruta_año):
            for mes in os.listdir(ruta_año):
                ruta_mes = os.path.join(ruta_año, mes)
                facturas = glob.glob(os.path.join(ruta_mes, "MERCADONA_*.pdf"))  

                for factura in facturas:
                    fecha_factura = re.search(r"(\d{4})(\d{2})(\d{2})", factura)  # Extraer fecha del nombre del archivo
                    if fecha_factura:
                        facturas_en_carpetas.append((factura, fecha_factura.group(0)))

    return facturas_en_carpetas

def procesar_facturas(facturas_a_procesar):
    if not facturas_a_procesar:
        print("✅ No hay facturas nuevas por procesar.")
        return

    facturas_procesadas = []
    
    for factura in facturas_a_procesar:
        imagenes = convert_from_path(factura)
        texto_extraido, precios_extraidos = extraer_texto(imagenes)
        fecha, establecimiento, total_pagar = extraer_metadatos(texto_extraido)
        
        productos_extraidos = []
        for j, linea in enumerate(texto_extraido.split("\n")):
            cantidad, descripcion, precio = procesar_linea(linea)
            if cantidad and descripcion:
                if j < len(precios_extraidos):
                    precio = float(precios_extraidos[j].replace(",", "."))
                productos_extraidos.append({
                    "cantidad": cantidad, "descripcion": descripcion, "precio": precio,
                    "fecha": fecha, "establecimiento": establecimiento, "total_pagar": total_pagar,
                    "articulos_detectados": len(productos_extraidos),
                    "precios_detectados": sum(1 for p in productos_extraidos if p["precio"] is not None)
                })

        facturas_procesadas.extend(productos_extraidos)
    return facturas_procesadas


if __name__ == "__main__":
    # Ruta base donde están organizadas las facturas
    ruta_base = "/home/carlos/workbenchPython/facturas/datos"

    # Procesa solo las facturas nuevas, evitando reprocesar las ya registradas
    # ultima_fecha_db = obtener_ultima_fecha()
    ultima_fecha_db = datetime.strptime('2025-01-01', "%Y-%m-%d")    
    # Se leen todas las carpetas
    facturas_en_carpetas = listar_facturas()
    # Se filtran las que no estan procesadas
    facturas_a_procesar = [f[0] for f in facturas_en_carpetas if datetime.strptime(f[1], "%Y%m%d") > ultima_fecha_db]  
    #
    if facturas_a_procesar:
    # Se procesan las que no estan procesadas
        facturas_procesadas=procesar_facturas(facturas_a_procesar)
    #BD. Crear la base de datos y la tabla 'facturas' si no existen
        conn, cursor = conectar_db()
        if conn is None or cursor is None:
            print('❌ Error de conexión con MySQL. No se pudo conectar a la BD.')
            crear_db()
            print("✅ Se ha creado BD MySQL")
        guardar_en_db(facturas_procesadas)
        print('--***--')            
        print("✅ Se ha actualizado la BD")
        print(f"✅ {len(facturas_a_procesar)} nuevas facturas fueron agregadas.")
        print(f"✅ {len(facturas_procesadas)} nuevos articulos fueron agregados.")
        # print(facturas_a_procesar)
