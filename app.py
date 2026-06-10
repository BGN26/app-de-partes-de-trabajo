from flask import Flask, render_template, redirect, url_for, request, flash
from flask.cli import load_dotenv
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Producto, ParteTrabajo
import os

load_dotenv()

app = Flask(__name__)


app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db.init_app(app)

# Configuración de Flask-Login para la seguridad
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Si alguien sin permiso intenta entrar, le manda aquí


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- RUTAS DE LA APLICACIÓN ---

@app.route('/')
def index():
    # Si ya está logueado, va al panel; si no, al login
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        # Comprobamos si el usuario existe y la contraseña encriptada coincide
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
@login_required  # ¡Seguridad activada! Solo usuarios logueados entran aquí
def dashboard():
    # Aquí cargaremos los partes de trabajo más adelante
    partes = ParteTrabajo.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', partes=partes)


# --- INICIALIZACIÓN Y DATOS DE PRUEBA ---

def crear_datos_prueba():
    with app.app_context():
        db.create_all()

        # 1. Usuario de prueba
        if not User.query.filter_by(username='admin').first():
            hashed_password = generate_password_hash('1234', method='pbkdf2:sha256')
            nuevo_usuario = User(username='admin', password_hash=hashed_password)
            db.session.add(nuevo_usuario)

        # 2. Productos/Materiales/Servicios de prueba (Petición de la BBDD)
        if not Producto.query.first():
            datos = [
                Producto(nombre="Mano de Obra - Tarifa Estándar (Hora)", precio=35.0),
                Producto(nombre="Mano de Obra - Tarifa Urgente (Hora)", precio=55.0),
                Producto(nombre="Cable de Red Cat6 (Metro)", precio=1.2),
                Producto(nombre="Tubería PVC 20mm (Metro)", precio=2.5),
                Producto(nombre="Interruptor Eléctrico Estándar", precio=8.90),
                Producto(nombre="Sustentación y Limpieza Técnica", precio=15.0)
            ]
            db.session.add_all(datos)

        db.session.commit()


@app.route('/parte/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_parte():

    productos = Producto.query.all()

    if request.method == 'POST':
        cliente = request.form.get('cliente')
        descripcion = request.form.get('descripcion')

        servicio_id = request.form.get('tipo_servicio')
        horas = float(request.form.get('horas', 0))

        material_id = request.form.get('material')
        cantidad_material = float(request.form.get('cantidad', 0))

        servicio = Producto.query.get(servicio_id)
        material = Producto.query.get(material_id)

        total_horas = servicio.precio * horas if servicio else 0
        total_materiales = material.precio * cantidad_material if material else 0
        total_calculado = total_horas + total_materiales

        materiales_texto = f"{horas}h de {servicio.nombre} + {cantidad_material}x {material.nombre}"


        nuevo_parte = ParteTrabajo(
            cliente=cliente,
            descripcion=descripcion,
            materiales_usados=materiales_texto,
            total_factura=round(total_calculado, 2),
            user_id=current_user.id
        )

        db.session.add(nuevo_parte)
        db.session.commit()

        flash('¡Parte de trabajo y simulación de factura guardados con éxito!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('form_parte.html', productos=productos)


if __name__ == '__main__':
    crear_datos_prueba()
    # Host 0.0.0.0 permite que ngrok o móviles en tu red accedan al puerto 5000
    app.run(host='0.0.0.0', port=5000, debug=True)