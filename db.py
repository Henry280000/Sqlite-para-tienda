import mysql.connector
from mysql.connector import Error

def create_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',        # Tu host
            database='inventario',   # Nombre de tu base de datos en mi caso es esta
            user='root',       # Tu usuario
            password=''   # Tu contraseña
        )
        return connection
    except Error as e:
        print(f"Error conectando a MySQL: {e}")
        return None

def get_all_products(db):
    try:
        cursor = db.cursor()
        cursor.execute("""
            SELECT id, numero_serie, nombre, descripcion, cantidad, precio, 
                   categoria_id, proveedor_id 
            FROM productos
        """)
        return cursor.fetchall()
    except Error as e:
        print(f"Error: {e}")
        return []

def get_product_by_id(db, product_id):
    try:
        cursor = db.cursor(dictionary=True)  # Esto retornará un diccionario
        cursor.execute("""
            SELECT id, numero_serie, nombre, descripcion, cantidad, precio, 
                   categoria_id, proveedor_id 
            FROM productos 
            WHERE id = %s
        """, (product_id,))
        return cursor.fetchone()
    except Error as e:
        print(f"Error: {e}")
        return None

def add_product(db, numero_serie, nombre, cantidad, precio, descripcion=None, categoria_id=None, proveedor_id=None):
    try:
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO productos (numero_serie, nombre, descripcion, cantidad, 
                                 precio, categoria_id, proveedor_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (numero_serie, nombre, descripcion, cantidad, precio, categoria_id, proveedor_id))
        db.commit()
        return True
    except Error as e:
        print(f"Error: {e}")
        return False

def update_product_details(db, product_id, nombre, descripcion, precio, categoria_id, proveedor_id):
    try:
        cursor = db.cursor()
        cursor.execute("""
            UPDATE productos 
            SET nombre = %s, descripcion = %s, precio = %s, 
                categoria_id = %s, proveedor_id = %s
            WHERE id = %s
        """, (nombre, descripcion, precio, categoria_id, proveedor_id, product_id))
        db.commit()
        return True
    except Error as e:
        print(f"Error: {e}")
        return False

def get_movements_by_product(db, product_id, fecha_inicio=None, fecha_fin=None, tipo=None):
    try:
        cursor = db.cursor(dictionary=True)
        query = """
            SELECT fecha, tipo, cantidad, stock_anterior, stock_posterior, 
                   precio, usuario, descripcion
            FROM movimientos
            WHERE producto_id = %s
        """
        params = [product_id]
        
        if fecha_inicio:
            query += " AND fecha >= %s"
            params.append(fecha_inicio)
        if fecha_fin:
            query += " AND fecha <= %s"
            params.append(fecha_fin)
        if tipo:
            query += " AND tipo = %s"
            params.append(tipo)
            
        query += " ORDER BY fecha DESC"
        
        cursor.execute(query, tuple(params))
        return cursor.fetchall()
    except Error as e:
        print(f"Error: {e}")
        return []
