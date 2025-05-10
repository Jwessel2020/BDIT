# app.py
import os # Added missing import for os module
import logging # Import logging module
from logging.handlers import RotatingFileHandler # For log rotation
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, abort
import random
from models import db, Project, Donation, User, ResourceRoute, ChildLocation, ChildProfile, Message, FieldAgentLocation
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from functools import wraps
from datetime import datetime
import json
from sqlalchemy import func # For sum aggregation
from decimal import Decimal

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ngo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'supersecretkey'  # Replace with a secure key
app.config['DEBUG'] = True # Explicitly enable Flask debug mode
db.init_app(app)

# --- Logging Setup ---
# Removed 'if not app.debug:' to ensure file logging is always active for troubleshooting
log_file = 'app.log'
file_handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024 * 100, backupCount=20)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.DEBUG) # Set to DEBUG to capture more details
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.DEBUG) # Set app logger to DEBUG
app.logger.info('NGO Operations Platform startup - File logging is active.')
# --- End Logging Setup ---

#####################################
# Flask-Login Configuration
#####################################
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def role_required(*roles):
    """
    Decorator to restrict route access to users with specific roles.
    """
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if current_user.role not in roles:
                # If not authorized, redirect to index or show a 403 error
                flash('You are not authorized to view this page.', 'danger')
                return redirect(url_for('index'))
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper

#####################################
# Routes for Authentication
#####################################
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            # Redirect based on role
            if user.role == 'mission_manager':
                return redirect(url_for('manager_dashboard'))
            elif user.role == 'field_agent':
                return redirect(url_for('field_agent'))
            elif user.role == 'donor':
                return redirect(url_for('donor'))
            elif user.role == 'child_care':
                return redirect(url_for('child_care'))
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))
        new_user = User(username=username, role=role)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

#####################################
# Application Routes
#####################################
@app.route('/')
@login_required
def index():
    # Redirect user to their specific dashboard based on role
    if current_user.role == 'mission_manager':
        return redirect(url_for('manager_dashboard'))
    elif current_user.role == 'field_agent':
        return redirect(url_for('field_agent'))
    elif current_user.role == 'donor':
        return redirect(url_for('donor'))
    elif current_user.role == 'child_care':
        return redirect(url_for('child_care'))
    return render_template('index.html') # Fallback, though ideally all roles have a specific landing page

@app.route('/field_agent')
@login_required
@role_required('field_agent', 'mission_manager') # MODIFIED: Allow mission_manager
def field_agent():
    agent_location = FieldAgentLocation.query.filter_by(user_id=current_user.id).order_by(FieldAgentLocation.timestamp.desc()).first()
    gps_data = {"latitude": -30.5595, "longitude": 22.9375} # Default
    if agent_location:
        gps_data = {"latitude": agent_location.lat, "longitude": agent_location.lon}
    # For a real app, fetch messages specific to this agent or their projects
    messages = Message.query.filter(
        (Message.recipient_id == current_user.id) |
        (Message.sender_id == current_user.id) # Consider project-specific channels too
    ).order_by(Message.timestamp.desc()).limit(10).all()
    return render_template('field_agent.html', gps_data=gps_data, messages=messages)

@app.route('/update_location', methods=['POST'])
@login_required
@role_required('field_agent')
def update_location():
    lat = round(random.uniform(-35, -22), 6)
    lon = round(random.uniform(16, 33), 6)
    # In a real app, you might associate this with an active project for the agent
    # project_id = get_current_project_for_agent(current_user.id) # Placeholder
    new_location = FieldAgentLocation(user_id=current_user.id, lat=lat, lon=lon, timestamp=datetime.now())
    db.session.add(new_location)
    db.session.commit()
    return jsonify({"success": True, "latitude": lat, "longitude": lon, "message": "Location updated successfully"})

@app.route('/donor')
@login_required
@role_required('donor', 'mission_manager') # MODIFIED: Allow mission_manager
def donor():
    # Example: Show total donations made by this donor
    total_donations_by_user = db.session.query(func.sum(Donation.donation_size)).filter_by(project_id=None).scalar() # Simplified example
    # In a real app, link donations to users
    donation_stats = {
        'total_donations': total_donations_by_user or 0,
        'projects_supported': Project.query.count(), # Example: count all projects
        'impact_score': random.randint(70, 95), # Placeholder
        'currency_trace': "USD → ZAR @ 18.5" # Placeholder
    }
    return render_template('donor.html', donation_stats=donation_stats)

@app.route('/child_care')
@login_required
@role_required('child_care', 'mission_manager') # MODIFIED: Allow mission_manager
def child_care():
    child_profiles = ChildProfile.query.all() # In a real app, filter by child care provider's assigned projects/children
    return render_template('child_care.html', child_profiles=child_profiles)

@app.route('/add_child_profile', methods=['GET', 'POST'])
@login_required
@role_required('child_care')
def add_child_profile():
    if request.method == 'POST':
        name = request.form.get('name')
        age = request.form.get('age')
        health_status = request.form.get('health_status')
        priority = request.form.get('priority')
        notes = request.form.get('notes')
        current_lat = request.form.get('current_lat')
        current_lon = request.form.get('current_lon')
        # project_id = request.form.get('project_id') # If assigning to a project during creation
        if name and age:
            new_profile = ChildProfile(name=name, age=int(age), health_status=health_status, priority=priority, notes=notes,
                                       current_lat=float(current_lat) if current_lat else None,
                                       current_lon=float(current_lon) if current_lon else None)
            db.session.add(new_profile)
            db.session.commit()
            flash('Child profile added successfully!', 'success')
            return redirect(url_for('child_care'))
        flash('Name and age are required!', 'danger')
    return render_template('add_child_profile.html')

# Reworked Manager Dashboard to list projects
@app.route('/manager_dashboard')
@login_required
@role_required('mission_manager')
def manager_dashboard():
    managed_projects = Project.query.filter_by(manager_id=current_user.id).order_by(Project.start_date.desc()).all()
    return render_template('manager_dashboard.html', projects=managed_projects)

# New route for displaying a single project's details
@app.route('/project/<int:project_id>')
@login_required
@role_required('mission_manager')
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    if project.manager_id != current_user.id:
        flash("You are not authorized to view this project.", "danger")
        return redirect(url_for('manager_dashboard'))

    # Financials - Sum of donations for this project
    project_donations_total_query = db.session.query(func.sum(Donation.donation_size)).filter_by(project_id=project.id).scalar()
    project_donations_total = Decimal(str(project_donations_total_query)) if project_donations_total_query is not None else Decimal('0.00')
    
    project_budget_decimal = Decimal(str(project.budget)) if project.budget is not None else Decimal('0.00')

    # DEBUG PRINTS
    print(f"DEBUG: project_budget_decimal type: {type(project_budget_decimal)}, value: {project_budget_decimal}")
    print(f"DEBUG: project_donations_total type: {type(project_donations_total)}, value: {project_donations_total}")

    project_financials = {
        'budget': project_budget_decimal,
        'donations_received': project_donations_total,
        'remaining_budget': project_budget_decimal - project_donations_total
    }
    print(f"DEBUG: remaining_budget type: {type(project_financials['remaining_budget'])}, value: {project_financials['remaining_budget']}") # DEBUG

    # Map data for this specific project
    project_resource_routes_query = ResourceRoute.query.filter_by(project_id=project.id).all()
    project_resource_routes_serializable = [
        {
            "origin": {"lat": route.origin_lat, "lon": route.origin_lon},
            "destination": {"lat": route.destination_lat, "lon": route.destination_lon},
            "resource_type": route.resource_type,
            "supply_quantity": route.supply_quantity
        }
        for route in project_resource_routes_query
    ]

    project_child_profiles = ChildProfile.query.filter_by(project_id=project.id).all()
    project_agent_locations_query = FieldAgentLocation.query.filter_by(project_id=project.id).order_by(FieldAgentLocation.timestamp.desc()).all()
    project_agent_locations_serializable = []
    # To avoid sending full user objects, select needed fields, e.g., username
    for loc in project_agent_locations_query:
        agent_user = User.query.get(loc.user_id)
        project_agent_locations_serializable.append({
            "lat": loc.lat,
            "lon": loc.lon,
            "name": agent_user.username if agent_user else f"Agent {loc.user_id}",
            "timestamp": loc.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        })

    # For child locations on map, use current_lat/lon from ChildProfile if available
    project_child_map_locations = [
        {"lat": cp.current_lat, "lon": cp.current_lon, "name": cp.name}
        for cp in project_child_profiles if cp.current_lat and cp.current_lon
    ]
    project_heat_data = [
        [d.destination_lat, d.destination_lon, d.donation_size]
        for d in Donation.query.filter_by(project_id=project.id).all()
    ]

    return render_template('project_detail.html',
                           project=project,
                           financials=project_financials,
                           resource_routes=project_resource_routes_serializable, # Use serializable version
                           child_locations=project_child_map_locations, # Use profiles with lat/lon
                           field_agent_locations=project_agent_locations_serializable, # Use serializable version
                           heat_data=project_heat_data)

# Unified Map Route (Global View)
@app.route('/map')
@login_required # All authenticated users can see the global map
def map_view():
    # This remains mostly the same, fetching all data for a global overview
    fund_tracing_example = {
        "origin": {"lat": -33.9249, "lon": 18.4241, "name": "Global HQ"},
        "destination": {"lat": -29.8587, "lon": 31.0218, "name": "Regional Office"},
        "donation_size": 25000,
        "donation_need": "Operational Support"
    }
    all_resource_routes_query = ResourceRoute.query.all()
    all_resource_routes_serializable = [
        {
            "origin": {"lat": route.origin_lat, "lon": route.origin_lon},
            "destination": {"lat": route.destination_lat, "lon": route.destination_lon},
            "resource_type": route.resource_type,
            "supply_quantity": route.supply_quantity
        }
        for route in all_resource_routes_query
    ]

    all_child_profiles_with_loc = ChildProfile.query.filter(ChildProfile.current_lat != None, ChildProfile.current_lon != None).all()
    all_child_map_locations = [
        {"lat": cp.current_lat, "lon": cp.current_lon, "name": cp.name}
        for cp in all_child_profiles_with_loc
    ]
    all_field_agent_locations = FieldAgentLocation.query.order_by(FieldAgentLocation.user_id, FieldAgentLocation.timestamp.desc()).all()
    latest_agent_locations_map = []
    seen_agents = set()
    for loc in all_field_agent_locations:
        if loc.user_id not in seen_agents:
            agent = User.query.get(loc.user_id)
            latest_agent_locations_map.append({
                "lat": loc.lat, "lon": loc.lon,
                "name": agent.username if agent else f"Agent {loc.user_id}",
                "timestamp": loc.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            })
            seen_agents.add(loc.user_id)
    
    all_donations = Donation.query.all()
    all_donation_routes_map = [
        {"origin": {"lat": d.origin_lat, "lon": d.origin_lon},
         "destination": {"lat": d.destination_lat, "lon": d.destination_lon},
         "donation_size": d.donation_size, "donation_need": d.donation_need}
        for d in all_donations
    ]
    all_heat_data = [[d.destination_lat, d.destination_lon, d.donation_size] for d in all_donations]

    return render_template("map.html",
                           fund_tracing=fund_tracing_example, # Example global fund trace
                           resource_routes=all_resource_routes_serializable, # Use serializable version
                           child_locations=all_child_map_locations,
                           donation_routes=all_donation_routes_map,
                           field_agent_locations=latest_agent_locations_map,
                           heat_data=all_heat_data,
                           is_global_map=True) # Flag to distinguish from project map

@app.route('/qr', methods=['GET', 'POST'])
@login_required
@role_required('field_agent', 'mission_manager')
def qr_scanner():
    if request.method == 'POST':
        if 'qrfile' not in request.files:
            flash('No file part in the request', 'danger')
            return redirect(url_for('qr_scanner'))
        file = request.files['qrfile']
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(url_for('qr_scanner'))
        from PIL import Image
        from pyzbar.pyzbar import decode
        try:
            image = Image.open(file)
            decoded_objects = decode(image)
            if decoded_objects:
                qr_data = decoded_objects[0].data.decode('utf-8')
                flash(f"QR Code Data: {qr_data}", 'success')
            else:
                flash('No valid QR code found.', 'warning')
        except Exception as e:
            flash(f"Error decoding QR code: {str(e)}", 'danger')
        return redirect(url_for('qr_scanner'))
    return render_template('qr.html')

from flask_socketio import SocketIO # Removed other imports as they are in messaging module
# Initialize SocketIO
os.environ['EVENTLET_NO_GREENDNS'] = 'yes' # For Python 3.12 with eventlet
try:
    import eventlet
    eventlet.monkey_patch()
    async_mode = 'eventlet'
except (ImportError, AttributeError):
    async_mode = 'threading'
socketio = SocketIO(app, async_mode=async_mode)

# Initialize the messaging module
from messaging import init_messaging
from messaging.scheduler import MessageScheduler

init_messaging(app, socketio) # Initialize messaging blueprint and socket events

# Pass app.app_context() to the MessageScheduler
message_scheduler = MessageScheduler(socketio, app.app_context)
message_scheduler.start()

@app.teardown_appcontext
def shutdown_scheduler(exception=None):
    message_scheduler.stop()

# Import CLI commands to register them
import cli  # noqa

if __name__ == '__main__':
    socketio.run(app, debug=True)

