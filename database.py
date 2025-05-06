import sqlite3
from sqlite3 import Error
from datetime import datetime

def create_connection():
    """Crear una conexión a la base de datos SQLite"""
    conn = None
    try:
        conn = sqlite3.connect('inventario.db')
        # Habilitar las claves foráneas
        conn.execute("PRAGMA foreign_keys = 1")
        return conn
    except Error as e:
        print(e)
    return conn

def create_tables(conn):
    """Crear tablas en la base de datos"""
    try:
        cursor = conn.cursor()
        
        # Tabla de Categorías
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            descripcion TEXT
        )
        ''')
        
        # Tabla de Proveedores
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS proveedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            contacto TEXT,
            telefono TEXT,
            email TEXT UNIQUE
        )
        ''')
        
        # Tabla de Productos
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_serie TEXT UNIQUE,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            cantidad INTEGER DEFAULT 0,
            precio REAL NOT NULL,
            categoria_id INTEGER,
            proveedor_id INTEGER,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (categoria_id) REFERENCES categorias (id) ON DELETE SET NULL,
            FOREIGN KEY (proveedor_id) REFERENCES proveedores (id) ON DELETE SET NULL
        )
        ''')
        
        # Tabla de Movimientos actualizada
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,  -- 'entrada' o 'salida'
            cantidad INTEGER NOT NULL,
            stock_anterior INTEGER NOT NULL,
            stock_posterior INTEGER NOT NULL,
            precio REAL NOT NULL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            usuario TEXT,
            descripcion TEXT,
            FOREIGN KEY (producto_id) REFERENCES productos (id) ON DELETE CASCADE
        )
        ''')
        
        conn.commit()
        return True
    except Error as e:
        print(f"Error al crear tablas: {e}")
        return False

# Funciones para INSERTAR datos (INSERT)

def insert_categoria(conn, nombre, descripcion=None):
    """Insertar una nueva categoría"""
    sql = '''INSERT INTO categorias(nombre, descripcion)
             VALUES(?, ?)'''
    try:
        cur = conn.cursor()
        cur.execute(sql, (nombre, descripcion))
        conn.commit()
        return cur.lastrowid
    except Error as e:
        print(f"Error al insertar categoría: {e}")
        return None

def insert_proveedor(conn, nombre, contacto=None, telefono=None, email=None):
    """Insertar un nuevo proveedor"""
    sql = '''INSERT INTO proveedores(nombre, contacto, telefono, email)
             VALUES(?, ?, ?, ?)'''
    try:
        cur = conn.cursor()
        cur.execute(sql, (nombre, contacto, telefono, email))
        conn.commit()
        return cur.lastrowid
    except Error as e:
        print(f"Error al insertar proveedor: {e}")
        return None

def add_product(conn, numero_serie, nombre, cantidad, precio, descripcion=None, categoria_id=None, proveedor_id=None):
    """Insertar un nuevo producto"""
    sql = '''INSERT INTO productos(numero_serie, nombre, descripcion, cantidad, precio, categoria_id, proveedor_id)
             VALUES(?, ?, ?, ?, ?, ?, ?)'''
    try:
        cur = conn.cursor()
        cur.execute(sql, (numero_serie, nombre, descripcion, cantidad, precio, categoria_id, proveedor_id))
        conn.commit()
        
        # Registrar el movimiento de entrada inicial
        if cantidad > 0:
            insert_movimiento(conn, cur.lastrowid, 'entrada', cantidad, 'Registro inicial del producto')
        
        return cur.lastrowid
    except Error as e:
        print(f"Error al insertar producto: {e}")
        return None

def insert_movimiento(conn, producto_id, tipo, cantidad, descripcion=None, usuario=None):
    """Insertar un nuevo movimiento de inventario"""
    try:
        cur = conn.cursor()
        
        # Obtener stock actual
        cur.execute("SELECT cantidad, precio FROM productos WHERE id = ?", (producto_id,))
        producto = cur.fetchone()
        if not producto:
            return None
            
        stock_anterior = producto[0]
        precio = producto[1]
        
        # Calcular stock posterior
        if tipo == 'entrada':
            stock_posterior = stock_anterior + cantidad
        else:  # salida
            stock_posterior = stock_anterior - cantidad
            if stock_posterior < 0:  # Evitar stock negativo
                return None
        
        # Insertar movimiento
        sql = '''INSERT INTO movimientos(
                    producto_id, tipo, cantidad, stock_anterior, 
                    stock_posterior, precio, descripcion, usuario
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)'''
        cur.execute(sql, (
            producto_id, tipo, cantidad, stock_anterior,
            stock_posterior, precio, descripcion, usuario
        ))
        
        # Actualizar stock en productos
        cur.execute(
            "UPDATE productos SET cantidad = ? WHERE id = ?",
            (stock_posterior, producto_id)
        )
        
        conn.commit()
        return cur.lastrowid
    except sqlite3.Error as e:
        print(f"Error al insertar movimiento: {e}")
        return None

# Funciones para INSERTAR datos masivos (para cumplir con los 15 registros por tabla)

def insert_initial_data(conn):
    """Insertar datos iniciales en todas las tablas (al menos 15 por tabla)"""
    
    # Insertar categorías
    categorias = [
        ("Electrónicos", "Productos electrónicos y gadgets"),
        ("Hogar", "Artículos para el hogar"),
        ("Oficina", "Útiles y mobiliario de oficina"),
        ("Cocina", "Utensilios y electrodomésticos de cocina"),
        ("Jardín", "Herramientas y artículos para jardín"),
        ("Deportes", "Equipamiento deportivo"),
        ("Juguetes", "Juguetes para niños"),
        ("Ropa", "Vestimenta y accesorios"),
        ("Calzado", "Todo tipo de calzado"),
        ("Libros", "Libros y material educativo"),
        ("Música", "Instrumentos y accesorios musicales"),
        ("Arte", "Materiales y obras de arte"),
        ("Mascotas", "Productos para mascotas"),
        ("Belleza", "Productos de belleza y cuidado personal"),
        ("Salud", "Artículos para la salud y bienestar")
    ]
    
    for cat in categorias:
        insert_categoria(conn, cat[0], cat[1])
    
    # Insertar proveedores
    proveedores = [
        ("TechMax", "Juan Pérez", "555-1234", "juan@techmax.com"),
        ("HomeGoods", "María López", "555-2345", "maria@homegoods.com"),
        ("OfficeSupply", "Carlos Ramírez", "555-3456", "carlos@officesupply.com"),
        ("GardenPro", "Ana Martínez", "555-4567", "ana@gardenpro.com"),
        ("SportWorld", "Pedro González", "555-5678", "pedro@sportworld.com"),
        ("ToyLand", "Sofía Díaz", "555-6789", "sofia@toyland.com"),
        ("FashionTrend", "Roberto Castro", "555-7890", "roberto@fashiontrend.com"),
        ("BookUniverse", "Laura Flores", "555-8901", "laura@bookuniverse.com"),
        ("MusicHub", "Diego Ortiz", "555-9012", "diego@musichub.com"),
        ("ArtStation", "Gabriela Morales", "555-0123", "gabriela@artstation.com"),
        ("PetShop", "Alejandro Vega", "555-1234", "alejandro@petshop.com"),
        ("BeautyClub", "Carmen Soto", "555-2345", "carmen@beautyclub.com"),
        ("HealthEssentials", "Fernando Ríos", "555-3456", "fernando@healthessentials.com"),
        ("KitchenPlus", "Valentina Torres", "555-4567", "valentina@kitchenplus.com"),
        ("TechGadgets", "Oscar Navarro", "555-5678", "oscar@techgadgets.com")
    ]
    
    for prov in proveedores:
        insert_proveedor(conn, prov[0], prov[1], prov[2], prov[3])
    
    # Insertar productos
    productos = [
        ("E001", "Laptop Dell XPS", "Laptop de alta gama", 10, 1299.99, 1, 1),
        ("E002", "Monitor LG 27\"", "Monitor 4K IPS", 15, 349.99, 1, 1),
        ("H001", "Juego de sábanas", "Algodón egipcio", 20, 99.99, 2, 2),
        ("H002", "Lámpara de mesa", "Diseño moderno", 12, 45.50, 2, 2),
        ("O001", "Escritorio ajustable", "Escritorio con altura regulable", 5, 249.99, 3, 3),
        ("O002", "Silla ergonómica", "Máximo confort", 8, 179.99, 3, 3),
        ("C001", "Batidora profesional", "5 velocidades", 7, 89.99, 4, 14),
        ("C002", "Juego de ollas", "Acero inoxidable", 10, 129.99, 4, 14),
        ("J001", "Cortacésped eléctrico", "Bajo consumo", 4, 199.99, 5, 4),
        ("J002", "Set de jardinería", "15 piezas", 15, 49.99, 5, 4),
        ("D001", "Bicicleta estática", "Con monitor cardíaco", 3, 349.99, 6, 5),
        ("D002", "Pelotas de tenis", "Paquete de 3", 30, 9.99, 6, 5),
        ("T001", "Muñeca interactiva", "Con sensor de voz", 20, 39.99, 7, 6),
        ("T002", "Set de bloques", "100 piezas", 15, 29.99, 7, 6),
        ("R001", "Camisa de algodón", "Talla M", 25, 24.99, 8, 7),
        ("Z001", "Tenis deportivos", "Nike talla 42", 12, 89.99, 9, 7),
        ("L001", "El principito", "Edición especial", 15, 19.99, 10, 8),
        ("M001", "Guitarra acústica", "Para principiantes", 5, 149.99, 11, 9),
        ("A001", "Set de pinturas", "Acrílicos profesionales", 10, 49.99, 12, 10),
        ("P001", "Cama para perro", "Tamaño mediano", 8, 34.99, 13, 11)
    ]
    
    for prod in productos:
        add_product(conn, prod[0], prod[1], prod[3], prod[4], prod[2], prod[5], prod[6])
    
    # Para completar 15 movimientos, agregar algunos movimientos adicionales
    movimientos_adicionales = [
        (1, "salida", 2, "Venta al cliente #123", "admin"),
        (2, "salida", 1, "Devolución por defecto", "admin"),
        (3, "entrada", 5, "Reposición de inventario", "admin"),
        (4, "salida", 3, "Venta a empresa XYZ", "admin"),
        (5, "entrada", 2, "Devolución de cliente", "admin"),
        (6, "salida", 1, "Muestra para cliente", "admin"),
        (7, "entrada", 10, "Compra a proveedor", "admin"),
        (8, "salida", 5, "Venta promocional", "admin"),
        (9, "entrada", 3, "Reposición de stock", "admin"),
        (10, "salida", 1, "Regalo corporativo", "admin")
    ]
    
    for mov in movimientos_adicionales:
        insert_movimiento(conn, mov[0], mov[1], mov[2], mov[3], mov[4])

# Funciones para CONSULTAR datos (SELECT)

def get_all_products(conn):
    """Obtener todos los productos"""
    cur = conn.cursor()
    cur.execute("SELECT * FROM productos")
    return cur.fetchall()

def get_product_by_id(db, product_id):
    cursor = db.cursor()
    try:
        cursor.execute("""
            SELECT id, numero_serie, nombre, descripcion, cantidad, precio, categoria_id, proveedor_id 
            FROM productos 
            WHERE id = ?
        """, (product_id,))
        producto = cursor.fetchone()
        if producto:
            return {
                'id': producto[0],
                'numero_serie': producto[1],
                'nombre': producto[2],
                'descripcion': producto[3],
                'cantidad': producto[4],
                'precio': producto[5],
                'categoria_id': producto[6],
                'proveedor_id': producto[7]
            }
    except sqlite3.Error as e:
        print(f"Error al obtener producto: {e}")
    return None

def get_products_with_details(conn):
    """Obtener productos con detalles de categoría y proveedor (JOIN)"""
    cur = conn.cursor()
    cur.execute('''
        SELECT p.id, p.numero_serie, p.nombre, p.cantidad, p.precio, 
               c.nombre as categoria, pv.nombre as proveedor
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id
        LEFT JOIN proveedores pv ON p.proveedor_id = pv.id
    ''')
    return cur.fetchall()

def get_all_categories(conn):
    """Obtener todas las categorías"""
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.id, c.nombre, c.descripcion,
                   COUNT(p.id) as total_productos
            FROM categorias c
            LEFT JOIN productos p ON c.id = p.categoria_id
            GROUP BY c.id, c.nombre, c.descripcion
            ORDER BY c.nombre
        """)
        return cur.fetchall()
    except sqlite3.Error as e:
        print(f"Error al obtener categorías: {e}")
        return []

def get_category_name(conn, categoria_id):
    """Obtener el nombre de una categoría específica"""
    try:
        cur = conn.cursor()
        cur.execute("SELECT nombre FROM categorias WHERE id = ?", (categoria_id,))
        resultado = cur.fetchone()
        return resultado[0] if resultado else "Categoría no encontrada"
    except sqlite3.Error as e:
        print(f"Error al obtener nombre de categoría: {e}")
        return "Error"

def get_products_by_category(conn, categoria_id):
    """Filtrar productos por categoría (WHERE)"""
    cur = conn.cursor()
    cur.execute("SELECT * FROM productos WHERE categoria_id = ?", (categoria_id,))
    return cur.fetchall()

def get_products_ordered_by_price(conn, order="ASC"):
    """Obtener productos ordenados por precio (ORDER BY)"""
    cur = conn.cursor()
    if order.upper() == "ASC":
        cur.execute("SELECT * FROM productos ORDER BY precio ASC")
    else:
        cur.execute("SELECT * FROM productos ORDER BY precio DESC")
    return cur.fetchall()

def get_inventory_value_by_category(conn):
    """Obtener valor del inventario agrupado por categoría (GROUP BY)"""
    cur = conn.cursor()
    cur.execute('''
        SELECT c.nombre as categoria, SUM(p.cantidad * p.precio) as valor_total
        FROM productos p
        JOIN categorias c ON p.categoria_id = c.id
        GROUP BY p.categoria_id
        HAVING valor_total > 0
        ORDER BY valor_total DESC
    ''')
    return cur.fetchall()

def get_movements_by_product(conn, product_id, fecha_inicio=None, fecha_fin=None, tipo=None):
    """Obtener movimientos de un producto específico"""
    try:
        cursor = conn.cursor()
        query = """
            SELECT m.fecha, m.tipo, m.cantidad, m.stock_anterior, m.stock_posterior, 
                   p.precio, m.usuario, m.descripcion
            FROM movimientos m
            JOIN productos p ON m.producto_id = p.id
            WHERE m.producto_id = ?
        """
        params = [product_id]
        
        if fecha_inicio:
            query += " AND m.fecha >= ?"
            params.append(fecha_inicio)
        if fecha_fin:
            query += " AND m.fecha <= ?"
            params.append(fecha_fin)
        if tipo:
            query += " AND m.tipo = ?"
            params.append(tipo)
            
        query += " ORDER BY m.fecha DESC"
        
        cursor.execute(query, tuple(params))
        movimientos = cursor.fetchall()
        
        # Convertir los resultados a diccionarios
        return [
            {
                'fecha': datetime.strptime(m[0], '%Y-%m-%d %H:%M:%S') if isinstance(m[0], str) else m[0],
                'tipo': m[1],
                'cantidad': m[2],
                'stock_anterior': m[3],
                'stock_posterior': m[4],
                'precio': m[5],
                'usuario': m[6],
                'descripcion': m[7],
                'tipo_badge': 'success' if m[1] == 'entrada' else 'danger',
                'cantidad_signo': '+' if m[1] == 'entrada' else '-'
            }
            for m in movimientos
        ]
    except sqlite3.Error as e:
        print(f"Error al obtener movimientos: {e}")
        return []

def get_low_stock_products(conn, threshold=5):
    """Obtener productos con stock bajo"""
    cur = conn.cursor()
    cur.execute("SELECT * FROM productos WHERE cantidad <= ?", (threshold,))
    return cur.fetchall()

# Funciones para ACTUALIZAR datos (UPDATE)

def update_product_quantity(conn, product_id, nueva_cantidad):
    """Actualizar la cantidad de un producto y registrar el movimiento"""
    try:
        cur = conn.cursor()
        
        # Obtener cantidad actual y precio
        cur.execute("SELECT cantidad, precio FROM productos WHERE id = ?", (product_id,))
        producto = cur.fetchone()
        
        if producto:
            cantidad_actual = producto[0]
            precio_actual = producto[1]
            diferencia = nueva_cantidad - cantidad_actual
            
            # Si hay diferencia, registrar el movimiento
            if diferencia != 0:
                # Determinar tipo de movimiento
                tipo = 'entrada' if diferencia > 0 else 'salida'
                cantidad_movimiento = abs(diferencia)
                
                # Comenzar transacción
                cur.execute("BEGIN TRANSACTION")
                
                try:
                    # Actualizar la cantidad en productos
                    cur.execute("""
                        UPDATE productos 
                        SET cantidad = ? 
                        WHERE id = ?
                    """, (nueva_cantidad, product_id))
                    
                    # Registrar el movimiento
                    cur.execute("""
                        INSERT INTO movimientos (
                            producto_id, tipo, cantidad, 
                            stock_anterior, stock_posterior,
                            precio, usuario, descripcion
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        product_id,
                        tipo,
                        cantidad_movimiento,
                        cantidad_actual,
                        nueva_cantidad,
                        precio_actual,
                        'sistema',
                        f'Actualización manual: {tipo} de {cantidad_movimiento} unidades'
                    ))
                    
                    # Confirmar transacción
                    conn.commit()
                    return True
                    
                except sqlite3.Error as e:
                    # Si hay error, revertir cambios
                    conn.rollback()
                    print(f"Error en la transacción: {e}")
                    return False
            
            return True  # No hay cambio en la cantidad
            
        return False  # Producto no encontrado
        
    except sqlite3.Error as e:
        print(f"Error al actualizar cantidad: {e}")
        return False

def update_product_price(conn, product_id, nuevo_precio):
    """Actualizar el precio de un producto"""
    try:
        cur = conn.cursor()
        cur.execute("UPDATE productos SET precio = ? WHERE id = ?", (nuevo_precio, product_id))
        conn.commit()
        return True
    except Error as e:
        print(f"Error al actualizar precio: {e}")
        return False

def update_product_details(conn, product_id, nombre=None, descripcion=None, precio=None, categoria_id=None, proveedor_id=None):
    """Actualizar detalles de un producto"""
    try:
        updates = []
        parameters = []
        
        if nombre:
            updates.append("nombre = ?")
            parameters.append(nombre)
        if descripcion:
            updates.append("descripcion = ?")
            parameters.append(descripcion)
        if precio:
            updates.append("precio = ?")
            parameters.append(precio)
        if categoria_id:
            updates.append("categoria_id = ?")
            parameters.append(categoria_id)
        if proveedor_id:
            updates.append("proveedor_id = ?")
            parameters.append(proveedor_id)
        
        if not updates:
            return False
        
        parameters.append(product_id)
        
        cur = conn.cursor()
        cur.execute(f"UPDATE productos SET {', '.join(updates)} WHERE id = ?", parameters)
        conn.commit()
        return True
    except Error as e:
        print(f"Error al actualizar producto: {e}")
        return False

# Funciones para ELIMINAR datos (DELETE)

def delete_product(conn, product_id):
    """Eliminar un producto por su ID"""
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM productos WHERE id = ?", (product_id,))
        conn.commit()
        return True
    except Error as e:
        print(f"Error al eliminar producto: {e}")
        return False

def delete_categoria(conn, categoria_id):
    """Eliminar una categoría por su ID"""
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM categorias WHERE id = ?", (categoria_id,))
        conn.commit()
        return True
    except Error as e:
        print(f"Error al eliminar categoría: {e}")
        return False

def delete_proveedor(conn, proveedor_id):
    """Eliminar un proveedor por su ID"""
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM proveedores WHERE id = ?", (proveedor_id,))
        conn.commit()
        return True
    except Error as e:
        print(f"Error al eliminar proveedor: {e}")
        return False

# Función para inicializar la base de datos
def initialize_database():
    """Inicializar la base de datos con tablas y datos iniciales"""
    conn = create_connection()
    if conn is not None:
        create_tables(conn)
        # Verificar si ya hay datos
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM productos")
        count = cur.fetchone()[0]
        
        if count == 0:
            # Insertar datos iniciales si la base de datos está vacía
            insert_initial_data(conn)
        
        conn.close()
    else:
        print("Error! No se pudo crear la conexión a la base de datos.")

# Si este script se ejecuta directamente, inicializar la base de datos
if __name__ == '__main__':
    initialize_database()