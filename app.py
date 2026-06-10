from flask import Flask, render_template, redirect, url_for, request, flash
from flask.cli import load_dotenv
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Cliente, Producto, ParteTrabajo, ParteMaterial
import os
import json

load_dotenv()

app = Flask(__name__)


app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_BINDS'] = {
    'clientes_db': os.getenv('BIND_CLIENTES'),
    'materiales_db': os.getenv('BIND_MATERIALES')
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))



@app.route('/')
def index():

    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()


        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():

    partes = ParteTrabajo.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', partes=partes)


def crear_datos_prueba():
    with app.app_context():
        # create_all mapea automáticamente la principal y todos los binds
        db.create_all()

        # 1. Cargar usuarios desde el archivo local usuarios.json
        if not User.query.filter_by(username='admin').first():
            hashed_admin = generate_password_hash('1234', method='pbkdf2:sha256')
            db.session.add(User(username='admin', password_hash=hashed_admin))

        if os.path.exists('usuarios.json'):
            with open('usuarios.json', 'r', encoding='utf-8') as f:
                usuarios_locales = json.load(f)
                for u in usuarios_locales:
                    # Si el usuario del JSON no existe en la BD, lo creamos
                    if not User.query.filter_by(username=u['username']).first():
                        pass_encriptada = generate_password_hash(u['password'], method='pbkdf2:sha256')
                        nuevo_usuario = User(username=u['username'], password_hash=pass_encriptada)
                        db.session.add(nuevo_usuario)
                        print(f"Usuario '{u['username']}' sincronizado desde usuarios.json")

        # 2. Cargar Falsos Clientes (irá a clientes.db automáticamente)
        if not Cliente.query.first():
            db.session.add_all([
                Cliente(nombre="Construcciones Alfa S.A.", direccion="Av. de la Industria 45, Madrid", cif="A1234567B"),
                Cliente(nombre="Talleres Mecánicos Martínez", direccion="Calle Falsa 123, Barcelona", cif="B9876543C")
            ])

        # 3. Cargar Falsos Productos (irá a materiales.db automáticamente)
        if not Producto.query.first():
            db.session.add_all([
                Producto(nombre="Instalación Estándar", precio_venta=40.0, es_servicio=True),
                Producto(nombre="Cable Coaxial RG6", proveedor="Televes", precio_venta=1.1, unidades_disponibles=500,
                         es_servicio=False),
                Producto(nombre="Router Inalámbrico AC1200", proveedor="Tp-Link", precio_venta=34.90,
                         unidades_disponibles=35, es_servicio=False)
            ])

        db.session.commit()


@app.route('/parte/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_parte():

    clientes = Cliente.query.all()
    servicios = Producto.query.filter_by(es_servicio=True).all()
    materiales = Producto.query.filter_by(es_servicio=False).all()

    if request.method == 'POST':
        cliente_id = request.form.get('cliente_id')
        servicio_id = request.form.get('servicio_id')
        horas = float(request.form.get('horas', 0))
        descripcion = request.form.get('descripcion')


        materiales_seleccionados = request.form.getlist('materiales[]')
        cantidades_seleccionadas = request.form.getlist('cantidades[]')


        servicio = Producto.query.get(servicio_id)
        total_calculado = servicio.precio_venta * horas


        nuevo_parte = ParteTrabajo(
            cliente_id=cliente_id,
            servicio_id=servicio_id,
            horas=horas,
            descripcion=descripcion,
            user_id=current_user.id,
            total_factura=0.0
        )
        db.session.add(nuevo_parte)
        db.session.flush()


        for mat_id, cant in zip(materiales_seleccionados, cantidades_seleccionadas):
            if mat_id and cant:
                cantidad = int(cant)
                if cantidad > 0:
                    mat = Producto.query.get(mat_id)
                    total_calculado += mat.precio_venta * cantidad


                    enlace = ParteMaterial(parte_id=nuevo_parte.id, producto_id=mat_id, cantidad=cantidad)
                    db.session.add(enlace)

                    # Restamos del stock disponible (Control de inventario temporal)
                    mat.unidades_disponibles -= cantidad

        nuevo_parte.total_factura = round(total_calculado, 2)
        db.session.commit()

        flash('Parte de trabajo registrado correctamente.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('form_parte.html', clientes=clientes, servicios=servicios, materiales=materiales)

if __name__ == '__main__':
    crear_datos_prueba()
    app.run(host='0.0.0.0', port=5000, debug=True)