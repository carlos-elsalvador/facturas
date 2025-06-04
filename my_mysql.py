import mysql.connector

# Configuración de conexión a MySQL
DB_HOST = "localhost"
DB_USER = "carlos"
DB_PASSWORD = "mc91067CEMC*"
DB_NAME = "facturas_super"

def conectar_db():
    """Conectar a la base de datos MySQL y verificar su existencia"""
    try:
        conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
        cursor = conn.cursor()
        return conn, cursor
    except mysql.connector.Error as err:
        return None, None  # Si la conexión falla, devolver None


def crear_db():
    """Crear la base de datos y la tabla 'facturas' si no existen"""
    conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD)
    cursor = conn.cursor()

    try:
        # Verificar si la base de datos ya existe
        cursor.execute("SHOW DATABASES")
        bases_existentes = [db[0] for db in cursor.fetchall()]

        if DB_NAME not in bases_existentes:
            cursor.execute(f"CREATE DATABASE {DB_NAME}")

        cursor.execute(f"USE {DB_NAME}")

        # Crear la tabla 'facturas' si no existe (con unicidad, UNIQUE)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facturas (
                id INT AUTO_INCREMENT PRIMARY KEY,
                cantidad INT,
                descripcion TEXT,
                precio FLOAT,
                fecha DATE,
                establecimiento VARCHAR(100),
                total_pagar FLOAT,
                articulos_detectados INT,
                precios_detectados INT,
                UNIQUE KEY unique_factura (fecha, establecimiento, descripcion(255), total_pagar)                       
            )
        """)

        conn.commit()
        print("Base de datos y tabla 'facturas' verificadas correctamente.")
    
    except mysql.connector.Error as err:
        print(f"[Error de MySQL] {err}")
    except Exception as e:
        print(f"[Error inesperado] {e}")
    finally:
        conn.close()  # Asegurar el cierre de conexión para evitar fugas de recursos



def guardar_en_db(facturas):
    """ Guarda los datos procesados en la base de datos MySQL """
    conn, cursor = conectar_db()
    if conn is None or cursor is None:
        return "Error: No se pudo conectar a la base de datos."

    for factura in facturas:
        cursor.execute("""
            INSERT IGNORE INTO facturas (cantidad, descripcion, precio, fecha, establecimiento, total_pagar, articulos_detectados, precios_detectados)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (factura["cantidad"], factura["descripcion"], factura["precio"], factura["fecha"], factura["establecimiento"], factura["total_pagar"], factura["articulos_detectados"], factura["precios_detectados"]))

    conn.commit()
    conn.close()


def obtener_ultima_fecha():
    """Consulta la última fecha de artículo en la base de datos"""
    conn, cursor = conectar_db()
    # Verificar si la tabla facturas existe 
    if conn is None or cursor is None:
        return "Error: La base de datos no existe."

    # Verificar si la tabla facturas existe
    cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'facturas'")

    if not cursor.fetchone():
        conn.close()
        return "Error: La tabla 'facturas' no existe en la base de datos."

    # Verificar si la tabla tiene datos
    cursor.execute("SELECT COUNT(*) FROM facturas")
    if cursor.fetchone()[0] == 0:
        conn.close()
        return "Error: La tabla 'facturas' no tiene datos."

    # Obtener la última fecha registrada
    cursor.execute("SELECT MAX(fecha) FROM facturas")
    ultima_fecha = cursor.fetchone()[0]  
    conn.close()
    
    return ultima_fecha if ultima_fecha else "2000-01-01"  # Si no hay datos, tomar una fecha muy antigua

