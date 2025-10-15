import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from functools import wraps
# Import a secure password hashing library
from werkzeug.security import generate_password_hash, check_password_hash

# --------------------------- Configuration ---------------------------

app = Flask(__name__)
# Get secret key from environment or use a fallback for development
app.secret_key = os.environ.get('SECRET_KEY', 'a_strong_fallback_secret_key_change_me_in_prod')

# Configure database - Use os.path.join for robust path handling
BASEDIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASEDIR, 'rental.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --------------------------- Decorators ---------------------------

def login_required(f):
    """Decorator to ensure user is logged in."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to ensure the logged-in user is an admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Always check for login first, though the route might have both
        if 'user_id' not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for('login'))
        
        if session.get('role') != 'admin':
            flash("Access denied. Admins only.", "danger")
            # Redirect to user dashboard if not admin
            return redirect(url_for('dashboard')) 
        return f(*args, **kwargs)
    return decorated_function

# --------------------------- Models ---------------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    username = db.Column(db.String(150), unique=True, nullable=False)
    # Store hashed password instead of plain text
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='user')
    
    # Method to set password securely
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # Method to check password securely
    def check_password(self, password):
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
    rent_per_day = db.Column(db.Float, nullable=False) # Changed to Float for better currency handling
    # Consider using a Boolean or a standard Enum for availability in a real-world app, 
    # but keeping as String for minimal change impact.
    availability = db.Column(db.String(20), nullable=False) 

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    gov_id = db.Column(db.String(100), nullable=False)
    license = db.Column(db.String(100), nullable=False)
    start_point = db.Column(db.String(100), nullable=False)
    end_point = db.Column(db.String(100), nullable=False)
    # Store dates as proper DateTime objects for easier calculation and comparison
    start_date = db.Column(db.DateTime, nullable=False) 
    end_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='Pending')
    payment_status = db.Column(db.String(20), default='Pending')
    amount_paid = db.Column(db.Float) # Changed to Float
    booked_on = db.Column(db.DateTime, default=datetime.utcnow) # Added timestamp for auditing

    user = db.relationship('User', backref='bookings')
    vehicle = db.relationship('Vehicle', backref='bookings')
    
    # Property to calculate rental days
    @property
    def rental_days(self):
        # Calculate days, ensure we handle cases where end_date is same as start_date
        return max(1, (self.end_date - self.start_date).days + 1)


# --------------------------- Helper Functions ---------------------------

def calculate_amount(vehicle, start_date_str, end_date_str):
    """Calculates the booking amount based on rent and days."""
    try:
        # Convert string dates to datetime objects
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        
        # Ensure dates are valid (start date is not after end date)
        if start_date > end_date:
            return None, "Start date cannot be after end date."

        # Calculate days, including the start day
        days = (end_date - start_date).days + 1
        
        # Calculate amount. Assuming the original code's logic of dividing by 2 (deposit/advance)
        amount = (vehicle.rent_per_day * days) / 2 
        
        return amount, days
    except ValueError:
        return None, "Invalid date format."


# --------------------------- Routes ---------------------------

@app.route('/')
def home():
    """Redirects authenticated users to their dashboard, otherwise to login."""
    if 'user_id' in session:
        return redirect(url_for('admin_dashboard' if session.get('role') == 'admin' else 'dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('account_created'):
        flash("Account created successfully! Please log in.", 'success')
        session.pop('account_created', None)

    if request.method == 'POST':
        # Find user by username
        user = User.query.filter_by(username=request.form.get('username')).first() 
        
        # Check if user exists AND if the password is correct using secure check_password method
        if user and user.check_password(request.form.get('password')):
            session['user_id'] = user.id
            session['role'] = user.role
            session['username'] = user.username # Store username for display
            flash(f"Welcome back, {user.full_name.split()[0]}!", 'success')
            return redirect(url_for('admin_dashboard' if user.role == 'admin' else 'dashboard'))

        flash("Invalid username or password.", 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.form
        
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        username = data.get('username')
        email = data.get('email')

        if password != confirm_password:
            flash("Passwords do not match.", 'danger')
            return redirect(url_for('register'))

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("Username or Email already exists.", 'danger')
            return redirect(url_for('register'))

        new_user = User(
            full_name=data.get('full_name'),
            email=email,
            username=username,
            # IMPORTANT: Use the set_password method to hash the password
            role=data.get('role', 'user') # 'role' field is for security, consider removing if only users register
        )
        new_user.set_password(password) # Set and hash the password
        
        try:
            db.session.add(new_user)
            db.session.commit()
            session['account_created'] = True
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash("An error occurred during registration.", 'danger')
            # Log the exception (recommended for real applications)
            # app.logger.error(f"Registration error: {e}") 
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    vehicles = Vehicle.query.filter_by(availability='Available').all() # Only show available vehicles
    # Add a filter option to the dashboard for users as well
    selected_type = request.args.get('type_filter')
    if selected_type and selected_type != 'all':
        vehicles = Vehicle.query.filter_by(availability='Available', type=selected_type).all()
        
    vehicle_types = db.session.query(Vehicle.type).distinct().all()
    
    return render_template('dashboard.html', 
                           vehicles=vehicles, 
                           vehicle_types=[t[0] for t in vehicle_types], 
                           selected_type=selected_type)

# ---
# Admin Routes
# ---

@app.route('/admin', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_dashboard():
    # Admin Vehicle Filter
    selected_filter = request.args.get('filter', 'all')
    vehicle_query = Vehicle.query
    if selected_filter != 'all':
        vehicle_query = vehicle_query.filter_by(type=selected_filter)
    vehicles = vehicle_query.all()

    # User Search/Booking Records
    user_records = []
    search_email = None
    
    # Handle POST request for searching users/bookings
    if request.method == 'POST':
        search_email = request.form.get('search_email')
        if search_email:
            # First, find the user
            user_to_find = User.query.filter_by(email=search_email).first()
            if user_to_find:
                # Then, fetch all bookings for that user
                user_records = Booking.query.filter_by(user_id=user_to_find.id).all()
            else:
                flash(f"No user found with email: {search_email}.", "info")

    # Fetch all users for management table
    all_users = User.query.all()
    # Fetch all bookings for management table, ordered by booked_on descending
    all_bookings = Booking.query.order_by(Booking.booked_on.desc()).all()

    return render_template('admin_dashboard.html', 
                           vehicles=vehicles, 
                           bookings=all_bookings, 
                           all_users=all_users,
                           user_records=user_records, 
                           search_email=search_email,
                           selected_filter=selected_filter)

# The rest of the admin routes are mostly fine in their logic but could be wrapped in try/except 
# blocks for better error handling. I'll focus on the major changes.

# ---
# Booking Routes
# ---

@app.route('/book/<int:vehicle_id>', methods=['GET', 'POST'])
@login_required
def book_vehicle(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)

    if vehicle.availability != 'Available':
        flash(f'Vehicle {vehicle.vehicle_id} is not available.', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        form_data = request.form
        
        # Basic validation for dates
        amount, days = calculate_amount(vehicle, form_data['start_date'], form_data['end_date'])
        if amount is None:
             flash(f'Invalid date range: {days}', 'danger')
             return render_template('book_vehicle.html', vehicle=vehicle) # Re-render form with error

        # Store booking data in session
        session['booking_info'] = {
            'vehicle_id': vehicle_id,
            'gov_id': form_data.get('gov_id'),
            'license': form_data.get('license'),
            'start_point': form_data.get('start_point'),
            'end_point': form_data.get('end_point'),
            'start_date': form_data.get('start_date'),
            'end_date': form_data.get('end_date'),
            'amount': amount, # Store calculated amount
            'days': days
        }
        return redirect(url_for('payment'))

    return render_template('book_vehicle.html', vehicle=vehicle)

@app.route('/payment', methods=['GET', 'POST'])
@login_required
def payment():
    booking_info = session.get('booking_info')
    if not booking_info:
        flash('No booking information found.', 'danger')
        return redirect(url_for('dashboard'))

    vehicle = Vehicle.query.get(booking_info['vehicle_id'])
    
    # Amount is now calculated and stored in session from the previous route
    amount = booking_info.get('amount')
    days = booking_info.get('days')

    if request.method == 'POST':
        try:
            # Convert string dates to datetime objects before saving to DB
            start_date_dt = datetime.strptime(booking_info['start_date'], '%Y-%m-%d')
            end_date_dt = datetime.strptime(booking_info['end_date'], '%Y-%m-%d')
            
            booking = Booking(
                user_id=session['user_id'],
                vehicle_id=booking_info['vehicle_id'],
                gov_id=booking_info['gov_id'],
                license=booking_info['license'],
                start_point=booking_info['start_point'],
                end_point=booking_info['end_point'],
                start_date=start_date_dt, # Storing as datetime object
                end_date=end_date_dt,     # Storing as datetime object
                status='Confirmed',
                payment_status='Paid',
                amount_paid=amount
            )
            db.session.add(booking)
            
            # Update vehicle availability
            vehicle.availability = 'Unavailable'
            
            db.session.commit()
            
            session.pop('booking_info', None)
            flash('Payment successful and booking confirmed!', 'success')
            return redirect(url_for('view_bookings')) # Redirect to view bookings instead of dashboard
        except Exception as e:
            db.session.rollback()
            flash("An error occurred during booking confirmation.", 'danger')
            # app.logger.error(f"Booking error: {e}")
            return redirect(url_for('dashboard'))


    return render_template('payment.html', vehicle=vehicle, booking_info=booking_info, amount=amount, days=days)


# ---
# Run App
# ---

# Removed 'add_admin' and 'remove_admin' as 'promote_user'/'demote_user' handle the role change.
# The original code's 'is_admin' logic was redundant/conflicting with the 'role' column.

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Check for admin user creation and dummy vehicle insertion
        if not User.query.filter_by(username="admin1").first():
            admin = User(
                full_name="Admin User",
                email="admin@example.com",
                username="admin1",
                role="admin"
            )
            # Securely set admin password
            admin.set_password("admin123") 
            db.session.add(admin)
            db.session.commit()
            
        insert_dummy_vehicles() # Called after create_all and admin creation

    app.run(debug=True)