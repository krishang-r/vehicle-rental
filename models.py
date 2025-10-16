from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='user')  # 'user' or 'admin'

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.String(20), unique=True, nullable=False)
    type = db.Column(db.String(50), nullable=False)
    make = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    color = db.Column(db.String(50), nullable=False)
    seating_capacity = db.Column(db.Integer, nullable=False)
    rent_per_day = db.Column(db.Integer, nullable=False)
    availability = db.Column(db.String(20), nullable=False)  # "Available" or "Unavailable"

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    gov_id = db.Column(db.String(100), nullable=False)
    license = db.Column(db.String(100), nullable=False)
    start_point = db.Column(db.String(100), nullable=False)
    end_point = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.String(50), nullable=False)
    end_date = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='Pending')
    payment_status = db.Column(db.String(20), default='Pending')
    amount_paid = db.Column(db.Integer)  # <-- add this line

    user = db.relationship('User', backref='bookings')
    vehicle = db.relationship('Vehicle', backref='bookings')
