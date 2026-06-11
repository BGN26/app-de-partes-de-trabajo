from flask import Flask, render_template, redirect, url_for, request, flash
from flask.cli import load_dotenv
from flask_login import (
    LoginManager,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Cliente, Producto, ParteTrabajo, ParteMaterial
import os
import json
from PIL import Image
from werkzeug.utils import secure_filename
from thefuzz import fuzz
import cv2
import google.generativeai as genai
from fpdf import FPDF
from flask import make_response

load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_BINDS"] = {
    "clientes_db": os.getenv("BIND_CLIENTES"),
    "materiales_db": os.getenv("BIND_MATERIALES"),
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

genai.configure(api_key=os.getenv("API_KEY"))

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("dashboard"))
        else:
            flash("Usuario o contraseña incorrectos", "error")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    partes = ParteTrabajo.query.filter_by(user_id=current_user.id).all()
    return render_template("dashboard.html", partes=partes)


def crear_datos_prueba():
    with app.app_context():
        db.create_all()

        if not User.query.filter_by(username="admin").first():
            hashed_admin = generate_password_hash("1234", method="pbkdf2:sha256")
            db.session.add(User(username="admin", password_hash=hashed_admin))

        if os.path.exists("usuarios.json"):
            with open("usuarios.json", "r", encoding="utf-8") as f:
                usuarios_locales = json.load(f)
                for u in usuarios_locales:
                    if not User.query.filter_by(username=u["username"]).first():
                        pass_encriptada = generate_password_hash(
                            u["password"], method="pbkdf2:sha256"
                        )
                        nuevo_usuario = User(
                            username=u["username"], password_hash=pass_encriptada
                        )
                        db.session.add(nuevo_usuario)
                        print(
                            f"Usuario '{u['username']}' sincronizado desde usuarios.json"
                        )

        if not Cliente.query.first():
            db.session.add_all(
                [
                    Cliente(
                        nombre="Construcciones Alfa S.A.",
                        direccion="Av. de la Industria 45, Madrid",
                        cif="A1234567B",
                    ),
                    Cliente(
                        nombre="Talleres Mecánicos Martínez",
                        direccion="Calle Falsa 123, Barcelona",
                        cif="B9876543C",
                    ),
                ]
            )

        if not Producto.query.first():
            db.session.add_all(
                [
                    Producto(
                        nombre="Instalación Estándar",
                        precio_venta=40.0,
                        es_servicio=True,
                    ),
                    Producto(
                        nombre="Cable Coaxial RG6",
                        proveedor="Televes",
                        precio_venta=1.1,
                        unidades_disponibles=500,
                        es_servicio=False,
                    ),
                    Producto(
                        nombre="Router Inalámbrico AC1200",
                        proveedor="Tp-Link",
                        precio_venta=34.90,
                        unidades_disponibles=35,
                        es_servicio=False,
                    ),
                ]
            )

        db.session.commit()


@app.route("/parte/nuevo", methods=["GET", "POST"])
@login_required
def nuevo_parte():
    clientes = Cliente.query.all()
    servicios = Producto.query.filter_by(es_servicio=True).all()
    materiales = Producto.query.filter_by(es_servicio=False).all()

    if request.method == "POST":
        cliente_id = request.form.get("cliente_id")
        servicio_id = request.form.get("servicio_id")
        horas = float(request.form.get("horas", 0))
        descripcion = request.form.get("descripcion")

        materiales_seleccionados = request.form.getlist("materiales[]")
        cantidades_seleccionadas = request.form.getlist("cantidades[]")

        servicio = Producto.query.get(servicio_id)
        total_calculado = servicio.precio_venta * horas if servicio else 0.0

        nuevo_parte = ParteTrabajo(
            cliente_id=cliente_id,
            servicio_id=servicio_id,
            horas=horas,
            descripcion=descripcion,
            user_id=current_user.id,
            total_factura=0.0,
        )
        db.session.add(nuevo_parte)
        db.session.flush()

        for mat_id, cant in zip(materiales_seleccionados, cantidades_seleccionadas):
            if mat_id and cant:
                cantidad = int(cant)
                if cantidad > 0:
                    mat = Producto.query.get(mat_id)
                    if mat:
                        total_calculado += mat.precio_venta * cantidad
                        enlace = ParteMaterial(
                            parte_id=nuevo_parte.id,
                            producto_id=mat_id,
                            cantidad=cantidad,
                        )
                        db.session.add(enlace)
                        mat.unidades_disponibles -= cantidad

        nuevo_parte.total_factura = round(total_calculado, 2)
        db.session.commit()

        flash("Parte de trabajo registrado correctamente.", "success")
        return redirect(url_for("dashboard"))

    return render_template(
        "form_parte.html", clientes=clientes, servicios=servicios, materiales=materiales
    )


@app.route("/parte/camara", methods=["GET", "POST"])
@login_required
def ocr_camara():
    if request.method == "POST":
        if "foto" not in request.files:
            flash("No se detectó ninguna imagen.", "error")
            return redirect(request.url)

        foto = request.files["foto"]
        if foto.filename == "":
            flash("No seleccionaste ninguna foto.", "error")
            return redirect(request.url)

        filename = secure_filename(foto.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        foto.save(filepath)

        ruta_procesada = os.path.join(
            app.config["UPLOAD_FOLDER"], "procesada_" + filename
        )

        try:
            img = cv2.imread(filepath)
            gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            gris = cv2.resize(
                gris, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_LINEAR
            )
            blur = cv2.GaussianBlur(gris, (5, 5), 0)
            binarizada = cv2.adaptiveThreshold(
                blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 4
            )
            cv2.imwrite(ruta_procesada, binarizada)
        except Exception as e:
            flash(f"Error procesando la imagen con OpenCV: {str(e)}", "error")
            return redirect(request.url)

        datos_ia = {
            "cliente": "",
            "descripcion_trabajo": "",
            "tipo de servicio": "",
            "materiales": [],
        }

        try:
            model = genai.GenerativeModel("gemini-2.5-flash")

            prompt = """
                    Analiza la siguiente imagen de un parte de trabajo y extrae los datos.
                    Devuelve SOLO un JSON con esta estructura exacta:
                    {
                        "cliente": "nombre del cliente",
                        "descripcion_trabajo": "tareas realizadas",
                        "tipo de servicio": "nombre del servicio",
                        "materiales": [
                            {"nombre": "nombre del material", "cantidad": 1}
                        ]
                    }
                    """

            with Image.open(ruta_procesada) as img_procesada:
                response = model.generate_content(
                    [prompt, img_procesada],
                    generation_config=genai.types.GenerationConfig(
                        response_mime_type="application/json",
                    ),
                )

            datos_ia = json.loads(response.text)

        except Exception as e:
            print(f"Error procesando la imagen con Gemini: {e}")
            flash("Hubo un error interpretando la imagen con IA.", "error")

        finally:
            if os.path.exists(filepath):
                os.remove(filepath)
            if os.path.exists(ruta_procesada):
                os.remove(ruta_procesada)

        def detectar_entidad_por_texto(
            lista_objetos, texto_buscar, umbral_seguro=85, umbral_dudoso=50
        ):
            if not texto_buscar:
                return None, False
            mejor_id = None
            mejor_puntuacion = 0
            texto_buscar = str(texto_buscar).lower()

            for item in lista_objetos:
                puntuacion = fuzz.partial_ratio(item.nombre.lower(), texto_buscar)
                if puntuacion > mejor_puntuacion:
                    mejor_puntuacion = puntuacion
                    mejor_id = item.id

            if mejor_puntuacion >= umbral_seguro:
                return mejor_id, False
            elif mejor_puntuacion >= umbral_dudoso:
                return mejor_id, True
            return None, False

        clientes = Cliente.query.all()
        servicios = Producto.query.filter_by(es_servicio=True).all()
        materiales = Producto.query.filter_by(es_servicio=False).all()

        cliente_id, cliente_dudoso = detectar_entidad_por_texto(
            clientes, datos_ia.get("cliente", "")
        )
        servicio_id, servicio_dudoso = detectar_entidad_por_texto(
            servicios, datos_ia.get("tipo de servicio", "")
        )

        materiales_procesados = []
        for mat_ia in datos_ia.get("materiales", []):
            nombre_mat = mat_ia.get("nombre", "")
            mat_id, mat_dudoso = detectar_entidad_por_texto(
                materiales, nombre_mat, umbral_seguro=85, umbral_dudoso=50
            )

            if mat_id:
                materiales_procesados.append(
                    {"id": mat_id, "cantidad": int(mat_ia.get("cantidad", 1))}
                )

        flash("Imagen analizada directamente por la IA con éxito.", "success")

        return render_template(
            "form_parte.html",
            clientes=clientes,
            servicios=servicios,
            materiales=materiales,
            texto_ocr=datos_ia.get("descripcion_trabajo", ""),
            cliente_detectado_id=cliente_id,
            cliente_dudoso=cliente_dudoso,
            servicio_detectado_id=servicio_id,
            servicio_dudoso=servicio_dudoso,
            materiales_detectados_json=json.dumps(materiales_procesados),
        )

    return render_template("captura_foto.html")


@app.route("/parte/ver/<int:id>")
@login_required
def ver_parte(id):
    parte = ParteTrabajo.query.get_or_404(id)

    cliente = Cliente.query.get(parte.cliente_id)
    servicio = Producto.query.get(parte.servicio_id)
    materiales_rel = ParteMaterial.query.filter_by(parte_id=id).all()

    materiales_utilizados = []
    for item in materiales_rel:
        prod = Producto.query.get(item.producto_id)
        if prod:
            materiales_utilizados.append(
                {
                    "nombre": prod.nombre,
                    "cantidad": item.cantidad,
                    "precio_u": prod.precio_venta,
                    "subtotal": round(prod.precio_venta * item.cantidad, 2),
                }
            )

    return render_template(
        "ver_parte.html",
        parte=parte,
        cliente=cliente,
        servicio=servicio,
        materiales=materiales_utilizados,
    )


@app.route("/parte/pdf/<int:id>")
@login_required
def generar_pdf(id):
    parte = ParteTrabajo.query.get_or_404(id)
    cliente = Cliente.query.get(parte.cliente_id)
    servicio = Producto.query.get(parte.servicio_id)
    materiales_rel = ParteMaterial.query.filter_by(parte_id=id).all()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(15, 15, 15)

    # Encabezado
    pdf.set_font("helvetica", "B", 18)
    pdf.cell(0, 10, "PARTE DE TRABAJO", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("helvetica", "", 10)
    pdf.cell(
        0,
        5,
        f"Documento de Control Interno N#: {parte.id}",
        new_x="LMARGIN",
        new_y="NEXT",
        align="C",
    )
    pdf.ln(10)

    # Datos del Cliente
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 7, "DATOS DEL CLIENTE:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 11)
    pdf.cell(
        0,
        6,
        f"Nombre / Razón Social: {cliente.nombre if cliente else 'No asignado'}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    if cliente:
        pdf.cell(0, 6, f"CIF/NIF: {cliente.cif}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 6, f"Direccion: {cliente.direccion}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    # Detalles del Servicio Realizado
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 7, "RESUMEN DE TRABAJOS:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 11)
    pdf.multi_cell(0, 6, f"Descripcion: {parte.descripcion}")
    pdf.ln(8)

    # Tabla de desglose de costos
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(90, 8, "Concepto / Articulo", border=1)
    pdf.cell(25, 8, "Cantidad", border=1, align="C")
    pdf.cell(30, 8, "Precio U.", border=1, align="R")
    pdf.cell(35, 8, "Total", border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("helvetica", "", 11)

    # Mano de obra
    if servicio:
        total_mano_obra = round(servicio.precio_venta * parte.horas, 2)
        pdf.cell(90, 8, f"Mano de obra: {servicio.nombre}", border=1)
        pdf.cell(25, 8, f"{parte.horas} h", border=1, align="C")
        pdf.cell(30, 8, f"{servicio.precio_venta} EUR", border=1, align="R")
        pdf.cell(
            35,
            8,
            f"{total_mano_obra} EUR",
            border=1,
            align="R",
            new_x="LMARGIN",
            new_y="NEXT",
        )

    # Materiales utilizados
    for item in materiales_rel:
        prod = Producto.query.get(item.producto_id)
        if prod:
            subtotal_mat = round(prod.precio_venta * item.cantidad, 2)
            pdf.cell(90, 8, prod.nombre, border=1)
            pdf.cell(25, 8, str(item.cantidad), border=1, align="C")
            pdf.cell(30, 8, f"{prod.precio_venta} EUR", border=1, align="R")
            pdf.cell(
                35,
                8,
                f"{subtotal_mat} EUR",
                border=1,
                align="R",
                new_x="LMARGIN",
                new_y="NEXT",
            )

    # Total
    pdf.ln(4)
    pdf.set_font("helvetica", "B", 13)
    pdf.cell(145, 10, "TOTAL IMPORTE:", align="R")
    pdf.cell(
        35, 10, f"{parte.total_factura} EUR", align="R", new_x="LMARGIN", new_y="NEXT"
    )

    response = make_response(bytes(pdf.output()))
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = (
        f"inline; filename=factura_parte_{parte.id}.pdf"
    )
    return response


@app.route("/parte/borrar/<int:id>", methods=["POST"])
@login_required
def borrar_parte(id):
    parte = ParteTrabajo.query.get_or_404(id)

    materiales_asociados = ParteMaterial.query.filter_by(parte_id=id).all()
    for item in materiales_asociados:
        prod = Producto.query.get(item.producto_id)
        if prod:
            prod.unidades_disponibles += item.cantidad
        db.session.delete(item)

    db.session.delete(parte)
    db.session.commit()

    flash("Parte de trabajo eliminado correctamente y stock restaurado.", "success")
    return redirect(url_for("dashboard"))


@app.route("/parte/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar_parte(id):
    parte = ParteTrabajo.query.get_or_404(id)
    clientes = Cliente.query.all()
    servicios = Producto.query.filter_by(es_servicio=True).all()
    materiales = Producto.query.filter_by(es_servicio=False).all()

    materiales_actuales = ParteMaterial.query.filter_by(parte_id=id).all()

    if request.method == "POST":
        for item in materiales_actuales:
            prod = Producto.query.get(item.producto_id)
            if prod:
                prod.unidades_disponibles += item.cantidad
            db.session.delete(item)

        db.session.flush()

        parte.cliente_id = request.form.get("cliente_id")
        parte.servicio_id = request.form.get("servicio_id")
        parte.horas = float(request.form.get("horas", 0))
        parte.descripcion = request.form.get("descripcion")

        nuevos_materiales = request.form.getlist("materiales[]")
        nuevas_cantidades = request.form.getlist("cantidades[]")

        servicio = Producto.query.get(parte.servicio_id)
        total_calculado = (servicio.precio_venta * parte.horas) if servicio else 0.0

        for mat_id, cant in zip(nuevos_materiales, nuevas_cantidades):
            if mat_id and cant:
                cantidad = int(cant)
                if cantidad > 0:
                    mat = Producto.query.get(mat_id)
                    if mat:
                        total_calculado += mat.precio_venta * cantidad
                        nuevo_enlace = ParteMaterial(
                            parte_id=parte.id, producto_id=mat_id, cantidad=cantidad
                        )
                        db.session.add(nuevo_enlace)
                        mat.unidades_disponibles -= cantidad

        parte.total_factura = round(total_calculado, 2)
        db.session.commit()

        flash("Parte de trabajo actualizado con éxito.", "success")
        return redirect(url_for("dashboard"))

    materiales_viejos_lista = []
    for item in materiales_actuales:
        materiales_viejos_lista.append(
            {"id": item.producto_id, "cantidad": item.cantidad}
        )

    return render_template(
        "form_parte.html",
        parte=parte,  # Pasamos el objeto del parte para saber que estamos EDITANDO
        clientes=clientes,
        servicios=servicios,
        materiales=materiales,
        texto_ocr=parte.descripcion,
        cliente_detectado_id=parte.cliente_id,
        servicio_detectado_id=parte.servicio_id,
        materiales_detectados_json=json.dumps(materiales_viejos_lista),
    )


if __name__ == "__main__":
    crear_datos_prueba()
    app.run(host="0.0.0.0", port=5000, debug=True)
