from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


class ParteTrabajo(db.Model):
    __tablename__ = "partes_trabajo"
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    descripcion = db.Column(db.Text, nullable=False)
    horas = db.Column(db.Float, default=0.0)
    total_factura = db.Column(db.Float, default=0.0)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    cliente_id = db.Column(db.Integer, nullable=False)
    servicio_id = db.Column(db.Integer, nullable=False)


class ParteMaterial(db.Model):
    __tablename__ = "parte_materiales"
    id = db.Column(db.Integer, primary_key=True)
    parte_id = db.Column(db.Integer, db.ForeignKey("partes_trabajo.id"), nullable=False)
    producto_id = db.Column(db.Integer, nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)


# clientes.db
class Cliente(db.Model):
    __tablename__ = "clientes"
    __bind_key__ = "clientes_db"  # <--- Vinculado a clientes.db
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    direccion = db.Column(db.String(200))
    cif = db.Column(db.String(20), unique=True, nullable=False)


# materiales.db
class Producto(db.Model):
    __tablename__ = "productos"
    __bind_key__ = "materiales_db"  # <--- Vinculado a materiales.db
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    proveedor = db.Column(db.String(100))
    coste_unitario = db.Column(db.Float, default=0.0)
    precio_venta = db.Column(db.Float, nullable=False)
    unidades_disponibles = db.Column(db.Integer, default=0)
    es_servicio = db.Column(db.Boolean, default=False)
