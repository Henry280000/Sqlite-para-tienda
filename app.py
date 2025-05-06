from flask import Flask, render_template, request, redirect, url_for, g, flash, send_file
import sqlite3
import pandas as pd
import pdfkit
from io import BytesIO
from datetime import datetime
from database import (
    create_connection, get_all_products, add_product, update_product_quantity, 
    delete_product, get_products_with_details, get_products_by_category,
    get_products_ordered_by_price, get_inventory_value_by_category,
    get_low_stock_products, update_product_price, update_product_details,
    get_movements_by_product, initialize_database, get_product_by_id,
    get_all_categories, get_category_name
)

app = Flask(__name__)
app.config['DATABASE'] = 'inventario.db'
app.config['SECRET_KEY'] = 'clave_secreta_para_flash'  # Necesario para mensajes flash

# En versiones recientes de Flask, reemplazamos before_first_request con un enfoque diferente
# Creamos una función para inicializar la base de datos
def init_app():
    with app.app_context():
        initialize_database()

# Llamar a init_app durante la inicialización
init_app()

def get_db():
    if 'db' not in g:
        g.db = create_connection()
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

@app.route('/')
def index():
    db = get_db()
    productos = get_all_products(db)
    return render_template('index.html', productos=productos, now=datetime.now())

# Ruta para mostrar productos con detalles (JOIN)
@app.route('/productos_detallados')
def productos_detallados():
    db = get_db()
    productos = get_products_with_details(db)
    return render_template('productos_detallados.html', productos=productos, now=datetime.now())

# Ruta para filtrar productos por categoría (WHERE)
@app.route('/productos_por_categoria', methods=['GET'])
@app.route('/productos_por_categoria/<int:categoria_id>', methods=['GET'])
def productos_por_categoria(categoria_id=None):
    db = get_db()
    try:
        # Obtener todas las categorías
        categorias = get_all_categories(db)
        
        if categoria_id:
            # Obtener productos de la categoría seleccionada
            productos = get_products_by_category(db, categoria_id)
            categoria_actual = next((cat[1] for cat in categorias if cat[0] == categoria_id), "Categoría no encontrada")
        else:
            productos = get_all_products(db)
            categoria_actual = "Todas las categorías"

        # Calcular estadísticas
        if productos:
            estadisticas = {
                'total_productos': len(productos),
                'valor_total': sum(float(p[5]) * float(p[4]) for p in productos),
                'stock_promedio': sum(float(p[4]) for p in productos) / len(productos),
                'productos_sin_stock': len([p for p in productos if int(p[4]) <= 0])
            }
        else:
            estadisticas = {
                'total_productos': 0,
                'valor_total': 0.0,
                'stock_promedio': 0.0,
                'productos_sin_stock': 0
            }

        return render_template(
            'productos_por_categoria.html',
            productos=productos,
            categorias=categorias,
            categoria_actual=categoria_actual,
            categoria_id=categoria_id,
            estadisticas=estadisticas,
            now=datetime.now()
        )
    except Exception as e:
        flash(f'Error al obtener productos: {str(e)}', 'error')
        return redirect(url_for('index'))

# Ruta para ordenar productos por precio (ORDER BY)
@app.route('/productos_por_precio/<order>')
def productos_por_precio(order):
    db = get_db()
    productos = get_products_ordered_by_price(db, order)
    orden = "ascendente" if order == "ASC" else "descendente"
    return render_template('productos_ordenados.html', productos=productos, orden=orden, now=datetime.now())

# Ruta para ver valor de inventario por categoría (GROUP BY, HAVING)
@app.route('/valor_por_categoria')
def valor_por_categoria():
    db = get_db()
    valores = get_inventory_value_by_category(db)
    return render_template('valor_inventario.html', valores=valores, now=datetime.now())

@app.route('/movimientos/<int:product_id>')
def movimientos(product_id):
    db = get_db()
    try:
        # Obtener parámetros de filtro
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        tipo_movimiento = request.args.get('tipo_movimiento')

        # Convertir fechas si están presentes
        if fecha_inicio:
            fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d')
        if fecha_fin:
            fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d')

        # Obtener datos del producto
        producto = get_product_by_id(db, product_id)
        if not producto:
            flash('Producto no encontrado', 'error')
            return redirect(url_for('index'))

        # Obtener movimientos
        movimientos = get_movements_by_product(db, product_id, fecha_inicio, fecha_fin, tipo_movimiento)

        # Calcular estadísticas
        estadisticas = {
            'total_entradas': sum(m['cantidad'] for m in movimientos if m['tipo'] == 'entrada'),
            'total_salidas': sum(m['cantidad'] for m in movimientos if m['tipo'] == 'salida'),
            'valor_total': sum(m['cantidad'] * m['precio'] for m in movimientos),
            'total_movimientos': len(movimientos)
        }

        return render_template('movimientos.html',
                             producto=producto,
                             movimientos=movimientos,
                             estadisticas=estadisticas,
                             now=datetime.now())
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/exportar_movimientos/<int:product_id>')
def exportar_movimientos(product_id):
    try:
        db = get_db()
        producto = get_product_by_id(db, product_id)
        movimientos = get_movements_by_product(db, product_id)

        # Crear DataFrame con pandas
        df = pd.DataFrame([{
            'Fecha': m['fecha'].strftime('%Y-%m-%d %H:%M:%S'),
            'Tipo': m['tipo'],
            'Cantidad': m['cantidad'],
            'Stock Anterior': m['stock_anterior'],
            'Stock Posterior': m['stock_posterior'],
            'Precio': m['precio'],
            'Usuario': m['usuario'],
            'Descripción': m['descripcion']
        } for m in movimientos])

        # Crear un buffer en memoria
        output = BytesIO()
        
        # Escribir el DataFrame en el buffer como Excel
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Movimientos', index=False)
            
            # Obtener la hoja de trabajo
            worksheet = writer.sheets['Movimientos']
            
            # Ajustar el ancho de las columnas
            for idx, col in enumerate(df.columns):
                max_length = max(df[col].astype(str).apply(len).max(), len(col))
                worksheet.set_column(idx, idx, max_length + 2)

        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'movimientos_{producto["nombre"]}_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )

    except Exception as e:
        flash(f'Error al exportar: {str(e)}', 'error')
        return redirect(url_for('movimientos_producto', product_id=product_id))

@app.route('/generar_pdf_movimientos/<int:product_id>')
def generar_pdf_movimientos(product_id):
    try:
        db = get_db()
        producto = get_product_by_id(db, product_id)
        movimientos = get_movements_by_product(db, product_id)
        
        # Renderizar el template HTML para el PDF
        html = render_template(
            'movimientos_pdf.html',
            producto=producto,
            movimientos=movimientos,
            now=datetime.now()
        )
        
        # Convertir HTML a PDF
        pdf = pdfkit.from_string(html, False)
        
        # Crear respuesta con el PDF
        response = send_file(
            BytesIO(pdf),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'movimientos_{producto["nombre"]}_{datetime.now().strftime("%Y%m%d")}.pdf'
        )
        
        return response

    except Exception as e:
        flash(f'Error al generar PDF: {str(e)}', 'error')
        return redirect(url_for('movimientos_producto', product_id=product_id))

# Ruta para stock bajo
@app.route('/stock_bajo')
def stock_bajo():
    db = get_db()
    threshold = request.args.get('threshold', 5, type=int)
    productos = get_low_stock_products(db, threshold)
    return render_template('stock_bajo.html', productos=productos, threshold=threshold, now=datetime.now())

@app.route('/agregar', methods=['GET', 'POST'])
def agregar_producto():
    if request.method == 'POST':
        numero_serie = request.form['numero_serie']
        nombre = request.form['nombre']
        descripcion = request.form.get('descripcion', '')
        cantidad = int(request.form['cantidad'])
        precio = float(request.form['precio'])
        categoria_id = request.form.get('categoria_id', None)
        if categoria_id == '':
            categoria_id = None
        proveedor_id = request.form.get('proveedor_id', None)
        if proveedor_id == '':
            proveedor_id = None
        
        db = get_db()
        result = add_product(db, numero_serie, nombre, cantidad, precio, descripcion, categoria_id, proveedor_id)
        
        if result:
            flash('Producto agregado correctamente', 'success')
        else:
            flash('Error al agregar el producto', 'error')
        
        return redirect(url_for('index'))
    
    # Si es GET, mostrar formulario de agregar
    return render_template('agregar_producto.html', now=datetime.now())

@app.route('/actualizar_producto/<int:product_id>', methods=['GET', 'POST'])
def actualizar_producto(product_id):
    db = get_db()
    
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            nombre = request.form.get('nombre')
            descripcion = request.form.get('descripcion')
            cantidad_agregar = int(request.form.get('cantidad_agregar', 0))
            cantidad_retirar = int(request.form.get('cantidad_retirar', 0))
            nuevo_precio = float(request.form.get('precio', 0.0))
            categoria_id = request.form.get('categoria_id')
            if categoria_id == '':
                categoria_id = None
            proveedor_id = request.form.get('proveedor_id')
            if proveedor_id == '':
                proveedor_id = None

            # Obtener producto actual
            producto_actual = get_product_by_id(db, product_id)
            if not producto_actual:
                flash('Producto no encontrado', 'error')
                return redirect(url_for('index'))

            cantidad_actual = producto_actual['cantidad']
            
            # Calcular nueva cantidad
            nueva_cantidad = cantidad_actual + cantidad_agregar - cantidad_retirar
            
            if nueva_cantidad < 0:
                flash('No se puede retirar más cantidad de la disponible', 'error')
                return redirect(url_for('actualizar_producto', product_id=product_id))

            # Actualizar la cantidad usando update_product_quantity
            if not update_product_quantity(db, product_id, nueva_cantidad):
                flash('Error al actualizar la cantidad', 'error')
                return redirect(url_for('actualizar_producto', product_id=product_id))

            # Actualizar otros detalles del producto
            if not update_product_details(
                db, product_id, 
                nombre=nombre,
                descripcion=descripcion,
                precio=nuevo_precio,
                categoria_id=categoria_id,
                proveedor_id=proveedor_id
            ):
                flash('Error al actualizar los detalles del producto', 'error')
                return redirect(url_for('actualizar_producto', product_id=product_id))

            flash('Producto actualizado correctamente', 'success')
            return redirect(url_for('index'))

        except ValueError as e:
            flash(f'Error en los datos ingresados: {str(e)}', 'error')
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
        
        return redirect(url_for('actualizar_producto', product_id=product_id))

    # Para GET request
    producto = get_product_by_id(db, product_id)
    if producto is None:
        flash('Producto no encontrado', 'error')
        return redirect(url_for('index'))
    
    # Asegurarse de que todos los valores necesarios estén presentes
    producto_data = {
        'id': producto['id'],
        'numero_serie': producto['numero_serie'],
        'nombre': producto['nombre'],
        'descripcion': producto['descripcion'],
        'cantidad': producto['cantidad'],
        'precio': producto['precio'],
        'categoria_id': producto['categoria_id'],
        'proveedor_id': producto['proveedor_id']
    }
    
    return render_template('actualizar_producto.html', 
                         producto=producto_data, 
                         now=datetime.now())

@app.route('/eliminar/<int:product_id>')
def eliminar_producto(product_id):
    db = get_db()
    result = delete_product(db, product_id)
    
    if result:
        flash('Producto eliminado correctamente', 'success')
    else:
        flash('Error al eliminar el producto', 'error')
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)