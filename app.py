import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash, session
import firebase_admin
from firebase_admin import credentials, firestore

# Construir el diccionario de configuración de Firebase desde las variables de entorno
firebase_config = {
    "type": os.getenv("FIREBASE_TYPE"),
    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
    "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace("\\n", "\n"),  # Asegúrate de reemplazar los saltos de línea en la clave privada
    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
    "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
    "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
    "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL"),
    "universe_domain": os.getenv("FIREBASE_UNIVERSE_DOMAIN")
}

# Inicializar Firebase con las credenciales
cred = credentials.Certificate(firebase_config)
firebase_admin.initialize_app(cred)

# Conectar a Firestore
db = firestore.client()

app = Flask(__name__)
app.secret_key = 'melisaris'

# Ruta de inicio de sesión para el administrador
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # Realizar la consulta usando `where`
        user_ref = db.collection('Admin').where('Correo', '==', email).where('Contrasena', '==', password).get()
        
        if user_ref:
            # Si se encuentra el usuario, se inicia sesión y se guarda su nombre en la sesión
            user_data = user_ref[0].to_dict()
            session['admin_logged_in'] = True
            session['admin_name'] = user_data['Nombre']
            flash(f"Bienvenido, {user_data['Nombre']}!")
            return redirect(url_for('admin_productos'))
        else:
            flash("Credenciales incorrectas")
            
    return render_template('login.html')



# Ruta de cierre de sesión para el administrador
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_name', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/productos')
def admin_productos():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    productos = db.collection('productos').stream()
    return render_template('productos_ad.html', productos=[p.to_dict() | {"id": p.id} for p in productos])

@app.route('/admin/productos/nuevo', methods=['GET', 'POST'])
def admin_agregar_producto():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        producto = {
            'nombre': request.form['nombre'],
            'categoria': request.form['categoria'],
            'precio': float(request.form['precio']),
            'descripcion': request.form['descripcion'],
            'cantidad': int(request.form['cantidad']),
            'imagen_url': request.form['imagen_url']
        }
        db.collection('productos').add(producto)
        return redirect(url_for('admin_productos'))
    return render_template('agregar_producto_ad.html')

@app.route('/admin/productos/editar/<id>', methods=['GET', 'POST'])
def admin_editar_producto(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    producto_ref = db.collection('productos').document(id)
    if request.method == 'POST':
        producto_ref.update({
            'nombre': request.form['nombre'],
            'categoria': request.form['categoria'],
            'precio': float(request.form['precio']),
            'descripcion': request.form['descripcion'],
            'cantidad': int(request.form['cantidad']),
            'imagen_url': request.form['imagen_url']
        })
        return redirect(url_for('admin_productos'))
    producto = producto_ref.get().to_dict()
    return render_template('agregar_producto_ad.html', producto=producto)

@app.route('/admin/productos/eliminar/<id>', methods=['POST'])
def admin_eliminar_producto(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    db.collection('productos').document(id).delete()
    flash("Producto eliminado correctamente.")
    return redirect(url_for('admin_productos'))

@app.route('/admin/productos/eliminar_confirmacion/<id>')
def admin_eliminar_producto_confirmacion(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    producto = db.collection('productos').document(id).get()
    if producto.exists:
        return render_template('eliminar.html', producto=producto.to_dict(), id=id)
    else:
        flash("Producto no encontrado.")
        return redirect(url_for('admin_productos'))

# Rutas para usuarios
@app.route('/')
@app.route('/productos')
def productos():
    nombre = request.args.get('nombre', '').strip().capitalize()
    categoria = request.args.get('categoria', '').strip()
    precio_min = request.args.get('precio_min', type=float, default=None)
    precio_max = request.args.get('precio_max', type=float, default=None)

    productos_ref = db.collection('productos')
    query = productos_ref
    
    try:
        if nombre:
            query = query.where('nombre', '==', nombre)
        if categoria:
            query = query.where('categoria', '==', categoria)
        if precio_min is not None:
            query = query.where('precio', '>=', precio_min)
        if precio_max is not None:
            query = query.where('precio', '<=', precio_max)

        productos = query.stream()
        productos = [p.to_dict() | {"id": p.id} for p in productos]

    except Exception as e:
        print(f"Error al realizar la consulta: {e}")
        productos = []
        flash("Error en la consulta. Por favor, verifica los filtros o crea los índices necesarios en Firestore.")

    categorias = {p.get('categoria') for p in db.collection('productos').stream()}
    
    return render_template('index.html', productos=productos, categorias=categorias, filtros={'nombre': nombre, 'categoria': categoria, 'precio_min': precio_min, 'precio_max': precio_max})

@app.route('/productos/<id>')
def producto_detalle(id):
    producto = db.collection('productos').document(id).get().to_dict()
    return render_template('detalle.html', producto=producto)
