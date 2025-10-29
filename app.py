from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, get_flashed_messages
import json
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from functools import wraps
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# Use an environment variable for secret key when available
app.secret_key = os.environ.get('SECRET_KEY', 'supersecretkey')

# Ensure instance folder exists and use a single DB in instance/
BASEDIR = os.path.abspath(os.path.dirname(__file__))
instance_dir = os.path.join(BASEDIR, 'instance')
os.makedirs(instance_dir, exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(instance_dir, 'rental.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --------------------------- Decorators ---------------------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please login first.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash("Access denied. Admins only.", "danger")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# --------------------------- Models ---------------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='user')

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
    availability = db.Column(db.String(20), nullable=False)

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
    amount_paid = db.Column(db.Integer)

    user = db.relationship('User', backref='bookings')
    vehicle = db.relationship('Vehicle', backref='bookings')

# --------------------------- Routes ---------------------------

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('account_created'):
        flash("Account created successfully!", 'success')
        session.pop('account_created', None)

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['role'] = user.role
            # If regular user, require selecting rental dates first
            if user.role != 'admin' and (not session.get('rental_start') or not session.get('rental_end')):
                return redirect(url_for('select_dates'))
            return redirect(url_for('admin_dashboard' if user.role == 'admin' else 'dashboard'))

        flash("Invalid username or password", 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.form
        if data['password'] != data['confirm_password']:
            flash("Passwords do not match", 'danger')
            return redirect(url_for('register'))

        # Normalize username and basic validation
        username = data['username'].strip()
        # Enforce username length between 8 and 12 characters
        if len(username) < 8 or len(username) > 12:
            flash("Username must be between 8 and 12 characters long.", 'danger')
            return redirect(url_for('register'))

        # Check if username is already taken
        if User.query.filter_by(username=username).first():
            flash("Username already exists", 'danger')
            return redirect(url_for('register'))

        # Check if email already exists
        if User.query.filter_by(email=data['email']).first():
            flash("Email already exists", 'danger')
            return redirect(url_for('register'))

        user = User(
            full_name=data['full_name'],
            email=data['email'],
            username=username,
            role=data.get('role', 'user')
        )
        # store hashed password
        user.set_password(data['password'])
        db.session.add(user)
        db.session.commit()
        session['account_created'] = True
        return redirect(url_for('login'))

    # For GET, gather any flashed messages and pass them into the template
    msgs = get_flashed_messages(with_categories=True)
    server_messages_json = json.dumps(msgs)
    return render_template('register.html', server_messages_json=server_messages_json)


@app.route('/check_username')
def check_username():
    """AJAX endpoint to check if a username is valid and available.
    Returns JSON: { available: bool, message: str }
    """
    username = request.args.get('username', '').strip()
    if not username:
        return jsonify(available=False, message='Enter a username')
    if len(username) < 8 or len(username) > 12:
        return jsonify(available=False, message='Username must be 8–12 characters')
    exists = User.query.filter_by(username=username).first()
    if exists:
        return jsonify(available=False, message='Username already taken')
    return jsonify(available=True, message='Username is available')

@app.route('/dashboard')
@login_required
def dashboard():
    # Require rental dates in session
    start = session.get('rental_start')
    end = session.get('rental_end')
    if not start or not end:
        flash('Please select rental dates first.', 'warning')
        return redirect(url_for('select_dates'))

    try:
        req_start = datetime.strptime(start, '%Y-%m-%d').date()
        req_end = datetime.strptime(end, '%Y-%m-%d').date()
    except Exception:
        flash('Invalid rental dates in session. Please select again.', 'danger')
        session.pop('rental_start', None)
        session.pop('rental_end', None)
        return redirect(url_for('select_dates'))

    # Find bookings that overlap the requested window and are not cancelled
    overlapping_bookings = Booking.query.filter(Booking.status != 'Cancelled').all()
    unavailable_vehicle_ids = set()
    for b in overlapping_bookings:
        try:
            b_start = datetime.strptime(b.start_date, '%Y-%m-%d').date()
            b_end = datetime.strptime(b.end_date, '%Y-%m-%d').date()
        except Exception:
            continue
        # overlap if booking_start <= req_end and booking_end >= req_start
        if b_start <= req_end and b_end >= req_start:
            unavailable_vehicle_ids.add(b.vehicle_id)

    vehicles = Vehicle.query.all()
    return render_template('dashboard.html', vehicles=vehicles, unavailable_vehicle_ids=unavailable_vehicle_ids,
                           rental_start=start, rental_end=end)

@app.route('/admin', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_dashboard():
    selected_filter = request.args.get('filter', 'all')
    vehicles = Vehicle.query.all() if selected_filter == 'all' else Vehicle.query.filter_by(type=selected_filter).all()
    bookings = Booking.query.all()

    user_records = []
    if request.method == 'POST':
        search_email = request.form.get('search_email')
        user = User.query.filter_by(email=search_email).first()
        if user:
            user_records = Booking.query.filter_by(user_id=user.id).all()
        else:
            flash("No user found with that email.", "warning")

    return render_template('admin_dashboard.html', vehicles=vehicles, bookings=bookings,
                           selected_filter=selected_filter, user_records=user_records)


@app.route('/select-dates', methods=['GET', 'POST'])
@login_required
def select_dates():
    # Allow user to pick rental start and end dates before viewing availability
    if request.method == 'POST':
        start = request.form.get('start')
        end = request.form.get('end')
        try:
            s = datetime.strptime(start, '%Y-%m-%d').date()
            e = datetime.strptime(end, '%Y-%m-%d').date()
            if e < s:
                flash('End date must be the same or after start date.', 'danger')
                return render_template('select_dates.html', rental_start=start, rental_end=end)
        except Exception:
            flash('Invalid dates provided. Use YYYY-MM-DD.', 'danger')
            return render_template('select_dates.html', rental_start=start, rental_end=end)

        session['rental_start'] = start
        session['rental_end'] = end
        return redirect(url_for('dashboard'))

    # GET
    return render_template('select_dates.html', rental_start=session.get('rental_start'), rental_end=session.get('rental_end'))


@app.route('/admin/add-vehicle', methods=['GET', 'POST'])
@admin_required
def add_vehicle():
    if request.method == 'POST':
        v = request.form
        new_vehicle = Vehicle(
            vehicle_id=v['vehicle_id'],
            type=v['type'],
            make=v['make'],
            model=v['model'],
            year=int(v['year']),
            color=v['color'],
            seating_capacity=int(v['seating_capacity']),
            rent_per_day=int(v['rent_per_day']),
            availability='Available'
        )
        db.session.add(new_vehicle)
        db.session.commit()
        flash("Vehicle added!", "success")
        return redirect(url_for('admin_dashboard'))
    return render_template('add_vehicle.html')

@app.route('/admin/delete-vehicle/<int:vehicle_id>')
@admin_required
def delete_vehicle(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    db.session.delete(vehicle)
    db.session.commit()
    flash("Vehicle deleted.", "warning")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update-rent/<int:vehicle_id>', methods=['POST'])
@admin_required
def update_rent(vehicle_id):
    vehicle = Vehicle.query.get(vehicle_id)
    vehicle.rent_per_day = int(request.form['new_rent'])
    db.session.commit()
    flash("Rent updated.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/promote/<int:user_id>')
@admin_required
def promote_user(user_id):
    user = User.query.get(user_id)
    if user:
        user.role = 'admin'
        db.session.commit()
        flash("User promoted to admin.", "info")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/demote/<int:user_id>')
@admin_required
def demote_user(user_id):
    if user_id == session['user_id']:
        flash("You can't demote yourself.", "danger")
        return redirect(url_for('admin_dashboard'))

    user = User.query.get(user_id)
    if user:
        user.role = 'user'
        db.session.commit()
        flash("Admin demoted to user.", "info")
    return redirect(url_for('admin_dashboard'))


@app.route('/add_admin', methods=['POST'])
@admin_required
def add_admin():
    email = request.form.get('email')
    user = User.query.filter_by(email=email).first()
    if user:
        user.role = 'admin'
        db.session.commit()
        flash(f"{email} is now an admin.", "success")
    else:
        flash(f"No user found with email {email}.", "danger")
    return redirect(url_for('admin_dashboard'))


@app.route('/remove_admin', methods=['POST'])
@admin_required
def remove_admin():
    email = request.form.get('email')
    user = User.query.filter_by(email=email).first()
    if user and user.role == 'admin':
        if user.id == session['user_id']:
            flash("You can't demote yourself.", "danger")
        else:
            user.role = 'user'
            db.session.commit()
            flash(f"{email} is no longer an admin.", "warning")
    else:
        flash(f"No admin found with email {email}.", "danger")
    return redirect(url_for('admin_dashboard'))



@app.route('/admin/cancel-booking/<int:booking_id>')
@admin_required
def admin_cancel_booking(booking_id):
    booking = Booking.query.get(booking_id)
    if booking:
        booking.status = 'Cancelled'
        booking.vehicle.availability = 'Available'
        db.session.commit()
        flash("Booking cancelled.", "warning")
    return redirect(url_for('admin_dashboard'))

@app.route('/my-bookings')
@login_required
def view_bookings():
    bookings = Booking.query.filter_by(user_id=session['user_id']).all()
    return render_template('bookings.html', bookings=bookings)

@app.route('/book/<int:vehicle_id>', methods=['GET', 'POST'])
@login_required
def book_vehicle(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    # Ensure rental dates are selected in session
    start = session.get('rental_start')
    end = session.get('rental_end')
    if not start or not end:
        flash('Please select rental dates before booking.', 'warning')
        return redirect(url_for('select_dates'))

    try:
        req_start = datetime.strptime(start, '%Y-%m-%d').date()
        req_end = datetime.strptime(end, '%Y-%m-%d').date()
    except Exception:
        flash('Invalid rental dates. Please select again.', 'danger')
        session.pop('rental_start', None)
        session.pop('rental_end', None)
        return redirect(url_for('select_dates'))

    # Check for overlapping bookings for this vehicle
    overlapping = Booking.query.filter(Booking.vehicle_id == vehicle.id, Booking.status != 'Cancelled').all()
    for b in overlapping:
        try:
            b_start = datetime.strptime(b.start_date, '%Y-%m-%d').date()
            b_end = datetime.strptime(b.end_date, '%Y-%m-%d').date()
        except Exception:
            continue
        if b_start <= req_end and b_end >= req_start:
            flash('This vehicle is not available for the selected dates.', 'danger')
            return redirect(url_for('dashboard'))

    # If POST, use submitted or session dates to create booking_info
    if request.method == 'POST':
        s_date = request.form.get('start_date') or start
        e_date = request.form.get('end_date') or end
        session['booking_info'] = {
            'vehicle_id': vehicle_id,
            'gov_id': request.form['gov_id'],
            'license': request.form['license'],
            'start_point': request.form['start_point'],
            'end_point': request.form['end_point'],
            'start_date': s_date,
            'end_date': e_date
        }
        return redirect(url_for('payment'))

    # Prefill form with rental dates from session
    return render_template('book_vehicle.html', vehicle=vehicle, prefill_start=start, prefill_end=end)

@app.route('/payment', methods=['GET', 'POST'])
@login_required
def payment():
    booking_info = session.get('booking_info')
    if not booking_info:
        flash('No booking info found.', 'danger')
        return redirect(url_for('dashboard'))

    vehicle = Vehicle.query.get(booking_info['vehicle_id'])
    start_date = datetime.strptime(booking_info['start_date'], '%Y-%m-%d')
    end_date = datetime.strptime(booking_info['end_date'], '%Y-%m-%d')
    days = (end_date - start_date).days + 1
    amount = (vehicle.rent_per_day * days) // 2

    if request.method == 'POST':
        booking = Booking(
            user_id=session['user_id'],
            vehicle_id=booking_info['vehicle_id'],
            gov_id=booking_info['gov_id'],
            license=booking_info['license'],
            start_point=booking_info['start_point'],
            end_point=booking_info['end_point'],
            start_date=booking_info['start_date'],
            end_date=booking_info['end_date'],
            status='Confirmed',
            payment_status='Paid',
            amount_paid=amount
        )
        db.session.add(booking)
        vehicle.availability = 'Unavailable'
        db.session.commit()
        session.pop('booking_info', None)
        flash('Payment successful and booking confirmed!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('payment.html', vehicle=vehicle, booking_info=booking_info, amount=amount)

@app.route('/cancel-booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != session['user_id']:
        flash("You are not authorized to cancel this booking.", "danger")
        return redirect(url_for('view_bookings'))

    booking.status = 'Cancelled'
    booking.vehicle.availability = 'Available'
    db.session.commit()
    flash("Booking cancelled successfully. Vehicle is now available.", "success")
    return redirect(url_for('view_bookings'))

@app.route('/admin/force-available/<int:vehicle_id>', methods=['POST'])
@admin_required
def force_available(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    vehicle.availability = 'Available'
    db.session.commit()
    flash("Vehicle marked as available manually.", "info")
    return redirect(url_for('admin_dashboard'))

@app.route('/logout', methods = ['GET', 'POST'])
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for('login'))

# --------------------------- Seed Data ---------------------------

def insert_dummy_vehicles():
    if Vehicle.query.first():
        return  # Prevent duplicate data on reruns

    dummy_vehicles = [
        # 🚗 Sedans
        Vehicle(vehicle_id="VR001", type="Sedan", make="Maruti", model="Swift", year=2022, color="White", seating_capacity=5, rent_per_day=1800, availability="Available"),
        Vehicle(vehicle_id="VR002", type="Sedan", make="Hyundai", model="i20", year=2023, color="Silver", seating_capacity=5, rent_per_day=1950, availability="Available"),
        Vehicle(vehicle_id="VR003", type="Sedan", make="Honda", model="Amaze", year=2021, color="Grey", seating_capacity=5, rent_per_day=2000, availability="Unavailable"),
        Vehicle(vehicle_id="VR004", type="Sedan", make="Tata", model="Tigor", year=2024, color="Blue", seating_capacity=5, rent_per_day=1850, availability="Available"),

        # 🚙 SUVs
        Vehicle(vehicle_id="VR005", type="SUV", make="Mahindra", model="XUV700", year=2024, color="Black", seating_capacity=7, rent_per_day=3500, availability="Available"),
        Vehicle(vehicle_id="VR006", type="SUV", make="Kia", model="Seltos", year=2023, color="White", seating_capacity=5, rent_per_day=2600, availability="Unavailable"),
        Vehicle(vehicle_id="VR007", type="SUV", make="Tata", model="Harrier", year=2023, color="Red", seating_capacity=5, rent_per_day=2800, availability="Available"),
        Vehicle(vehicle_id="VR008", type="SUV", make="Hyundai", model="Creta", year=2022, color="Black", seating_capacity=5, rent_per_day=2700, availability="Available"),

        # 🚘 Hatchbacks
        Vehicle(vehicle_id="VR009", type="Hatchback", make="Maruti", model="Baleno", year=2023, color="Red", seating_capacity=5, rent_per_day=1700, availability="Available"),
        Vehicle(vehicle_id="VR010", type="Hatchback", make="Hyundai", model="Grand i10 Nios", year=2022, color="White", seating_capacity=5, rent_per_day=1650, availability="Available"),

        # 🏍️ Bikes
        Vehicle(vehicle_id="VR011", type="Bike", make="Royal Enfield", model="Classic 350", year=2023, color="Black", seating_capacity=2, rent_per_day=1000, availability="Available"),
        Vehicle(vehicle_id="VR012", type="Bike", make="Bajaj", model="Pulsar 220F", year=2022, color="Blue", seating_capacity=2, rent_per_day=850, availability="Available"),
        Vehicle(vehicle_id="VR013", type="Bike", make="Honda", model="CB Hornet", year=2021, color="Red", seating_capacity=2, rent_per_day=800, availability="Unavailable"),
        Vehicle(vehicle_id="VR014", type="Bike", make="TVS", model="Apache RTR", year=2023, color="White", seating_capacity=2, rent_per_day=900, availability="Available"),

        # 🚗 Luxury Cars
        Vehicle(vehicle_id="VR015", type="Luxury", make="BMW", model="5 Series", year=2024, color="Black", seating_capacity=5, rent_per_day=7000, availability="Available"),
        Vehicle(vehicle_id="VR016", type="Luxury", make="Audi", model="A6", year=2023, color="White", seating_capacity=5, rent_per_day=7500, availability="Available"),
        Vehicle(vehicle_id="VR017", type="Luxury", make="Mercedes", model="E-Class", year=2023, color="Grey", seating_capacity=5, rent_per_day=8000, availability="Unavailable"),

        # 🛻 Others
        Vehicle(vehicle_id="VR018", type="Pickup", make="Isuzu", model="D-Max", year=2022, color="Silver", seating_capacity=5, rent_per_day=3200, availability="Available"),
        Vehicle(vehicle_id="VR019", type="Van", make="Toyota", model="Innova", year=2021, color="Beige", seating_capacity=7, rent_per_day=3000, availability="Available"),
        Vehicle(vehicle_id="VR020", type="Luxury", make="Jaguar", model="XF", year=2024, color="Blue", seating_capacity=5, rent_per_day=8500, availability="Available")
    ]

    db.session.add_all(dummy_vehicles)
    db.session.commit()

# --------------------------- Run App ---------------------------

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        insert_dummy_vehicles()

        if not User.query.filter_by(username="admin1").first():
            admin = User(
                full_name="Admin User",
                email="admin@example.com",
                username="admin1",
                role="admin"
            )
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()

    app.run(debug=True)
