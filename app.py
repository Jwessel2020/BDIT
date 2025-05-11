# app.py
import os # Added missing import for os module
import logging # Import logging module
from logging.handlers import RotatingFileHandler # For log rotation
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, abort
import random
from models import db, Project, Donation, User, ResourceRoute, ChildLocation, ChildProfile, Message, FieldAgentLocation, Crisis
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
@role_required('donor', 'mission_manager')
def donor():
    # Fetch donations made by the current user
    user_donations = Donation.query.filter_by(donor_id=current_user.id).order_by(Donation.timestamp.asc()).all()

    # Data for Donation History (Time-Series)
    donation_history_timestamps = []
    cumulative_donor_donations = []
    current_donor_cumulative = Decimal('0.00')
    total_donations_by_user_value = Decimal('0.00')

    for don in user_donations:
        donation_history_timestamps.append(don.timestamp.strftime('%Y-%m-%d'))
        current_donor_cumulative += Decimal(str(don.donation_size))
        cumulative_donor_donations.append(float(current_donor_cumulative))
        total_donations_by_user_value += Decimal(str(don.donation_size))

    # Data for Donations by Project (Pie Chart)
    donations_by_project_data = {}
    for don in user_donations:
        if don.project_id:
            project_name = don.project.name if don.project else "Unknown Project"
            donations_by_project_data[project_name] = donations_by_project_data.get(project_name, Decimal('0.00')) + Decimal(str(don.donation_size))
        else:
            donations_by_project_data["General Aid (Unassigned)"] = donations_by_project_data.get("General Aid (Unassigned)", Decimal('0.00')) + Decimal(str(don.donation_size))
    
    project_labels = list(donations_by_project_data.keys())
    project_values = [float(val) for val in donations_by_project_data.values()]

    # Original donation_stats (can be simplified or enhanced)
    # We now have a more accurate total_donations_by_user_value
    donation_stats = {
        'total_donations': float(total_donations_by_user_value),
        'projects_supported': len(set(don.project_id for don in user_donations if don.project_id)), # Count unique projects supported
        'impact_score': random.randint(70, 95), # Placeholder, can be made more sophisticated
        'currency_trace': "USD → ZAR @ 18.5" # Placeholder
    }

    return render_template('donor.html', 
                           donation_stats=donation_stats,
                           donation_history_timestamps=donation_history_timestamps,
                           cumulative_donor_donations=cumulative_donor_donations,
                           project_labels=project_labels,
                           project_values=project_values
                           )

@app.route('/child_care')
@login_required
@role_required('child_care', 'mission_manager')
def child_care():
    child_profiles = ChildProfile.query.all()

    # Data for Age Distribution Bar Chart
    age_bins = {"0-2": 0, "3-5": 0, "6-10": 0, "11-14": 0, "15-18": 0, "Other": 0}
    for child in child_profiles:
        age = child.age
        if 0 <= age <= 2:
            age_bins["0-2"] += 1
        elif 3 <= age <= 5:
            age_bins["3-5"] += 1
        elif 6 <= age <= 10:
            age_bins["6-10"] += 1
        elif 11 <= age <= 14:
            age_bins["11-14"] += 1
        elif 15 <= age <= 18:
            age_bins["15-18"] += 1
        else:
            age_bins["Other"] += 1
    age_distribution_labels = list(age_bins.keys())
    age_distribution_values = list(age_bins.values())

    # Data for Health Status Pie Chart
    health_status_counts = {}
    for child in child_profiles:
        status = child.health_status if child.health_status else "Unknown"
        health_status_counts[status] = health_status_counts.get(status, 0) + 1
    
    health_status_labels = list(health_status_counts.keys())
    health_status_values = list(health_status_counts.values())

    # Data for Urgency Score Chart
    urgency_score_counts = {str(i): 0 for i in range(1, 11)} # Initialize for scores 1-10
    urgency_score_counts['Other/None'] = 0
    for child in child_profiles:
        score = str(child.urgency_score) if child.urgency_score in range(1, 11) else 'Other/None'
        urgency_score_counts[score] = urgency_score_counts.get(score, 0) + 1
    
    urgency_labels = list(urgency_score_counts.keys())
    urgency_values = list(urgency_score_counts.values())

    return render_template('child_care.html', 
                           child_profiles=child_profiles,
                           age_distribution_labels=age_distribution_labels,
                           age_distribution_values=age_distribution_values,
                           health_status_labels=health_status_labels,
                           health_status_values=health_status_values,
                           urgency_labels=urgency_labels,
                           urgency_values=urgency_values
                           )

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

    # Data for Overall Project Status Pie Chart
    status_counts = {
        'Planning': 0, 'Ongoing': 0, 'Completed': 0, 'On Hold': 0, 'Other': 0
    }
    for project in managed_projects:
        if project.status in status_counts:
            status_counts[project.status] += 1
        else:
            status_counts['Other'] += 1 # Catch any other statuses
    
    chart_status_labels = [status for status, count in status_counts.items() if count > 0]
    chart_status_values = [count for status, count in status_counts.items() if count > 0]

    # Data for Total Portfolio Financials Bar Chart
    total_budget_all_projects = Decimal('0.00')
    total_donations_all_projects = Decimal('0.00')

    for project in managed_projects:
        total_budget_all_projects += Decimal(str(project.budget)) if project.budget else Decimal('0.00')
        project_donations = db.session.query(func.sum(Donation.donation_size)).filter_by(project_id=project.id).scalar()
        total_donations_all_projects += Decimal(str(project_donations)) if project_donations else Decimal('0.00')

    portfolio_financial_labels = ['Total Budget', 'Total Donations Received']
    portfolio_financial_values = [float(total_budget_all_projects), float(total_donations_all_projects)]

    return render_template('manager_dashboard.html', 
                           projects=managed_projects,
                           status_labels=chart_status_labels,
                           status_values=chart_status_values,
                           portfolio_financial_labels=portfolio_financial_labels,
                           portfolio_financial_values=portfolio_financial_values
                           )

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

    # Prepare data for Donation Trend chart
    donations_for_project = Donation.query.filter_by(project_id=project.id).order_by(Donation.timestamp.asc()).all()
    donation_timestamps = []
    cumulative_donations = []
    current_cumulative = Decimal('0.00')
    for don in donations_for_project:
        donation_timestamps.append(don.timestamp.strftime('%Y-%m-%d')) # Format for chart
        current_cumulative += Decimal(str(don.donation_size))
        cumulative_donations.append(float(current_cumulative)) # Plotly prefers float

    return render_template('project_detail.html',
                           project=project,
                           financials=project_financials,
                           resource_routes=project_resource_routes_serializable, 
                           child_locations=project_child_map_locations, 
                           field_agent_locations=project_agent_locations_serializable, 
                           heat_data=project_heat_data,
                           donation_timestamps=donation_timestamps, # NEW data for chart
                           cumulative_donations=cumulative_donations) # NEW data for chart

# Endpoint to update project status
@app.route('/project/<int:project_id>/update_status', methods=['POST'])
@login_required
@role_required('mission_manager')
def update_project_status(project_id):
    project = Project.query.get_or_404(project_id)
    if project.manager_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    data = request.get_json()
    new_status = data.get('new_status')

    if not new_status:
        return jsonify({'success': False, 'message': 'New status not provided'}), 400

    # Optional: Add validation for allowed statuses
    allowed_statuses = ['Planning', 'Ongoing', 'On Hold', 'Completed']
    if new_status not in allowed_statuses:
        return jsonify({'success': False, 'message': f'Invalid status: {new_status}'}), 400

    try:
        project.status = new_status
        db.session.commit()
        app.logger.info(f"Project {project.id} status updated to {new_status} by manager {current_user.username}")
        return jsonify({'success': True, 'new_status': new_status, 'message': 'Project status updated successfully.'})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating project {project.id} status: {str(e)}")
        return jsonify({'success': False, 'message': 'Error updating status.'}), 500

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

# New Route for Crisis Response Dashboard
@app.route('/crisis_dashboard')
@login_required
@role_required('mission_manager') # Or other roles as appropriate
def crisis_dashboard():
    crises = Crisis.query.order_by(Crisis.start_date.desc()).all()
    # Later, we can add logic here to fetch details for a specific crisis if an ID is provided
    return render_template('crisis_dashboard.html', crises=crises)

# API Endpoint to get details for a specific crisis
@app.route('/api/crisis/<int:crisis_id>/details')
@login_required
@role_required('mission_manager')
def api_crisis_details(crisis_id):
    crisis = Crisis.query.get_or_404(crisis_id)

    children_in_crisis = []
    for child in crisis.children_assigned.order_by(ChildProfile.urgency_score.desc().nullslast(), ChildProfile.priority.desc()):
        children_in_crisis.append({
            'id': child.id,
            'name': child.name,
            'age': child.age,
            'health_status': child.health_status,
            'priority': child.priority,
            'urgency_score': child.urgency_score,
            'notes': child.notes[:100] + '...' if child.notes and len(child.notes) > 100 else child.notes,
            'lat': child.current_lat, # ADDED for map marker
            'lon': child.current_lon  # ADDED for map marker
        })

    resources_for_crisis = []
    for route in crisis.resource_routes_targeted.all(): 
        resources_for_crisis.append({
            'id': route.id,
            'resource_type': route.resource_type,
            'supply_quantity': route.supply_quantity,
            'status': route.status,
            'assigned_agent': route.assigned_agent.username if route.assigned_agent else 'N/A',
            'origin_lat': route.origin_lat,       # ADDED for map route
            'origin_lon': route.origin_lon,       # ADDED for map route
            'destination_lat': route.destination_lat, # ADDED for map route
            'destination_lon': route.destination_lon  # ADDED for map route
        })
    
    involved_agent_ids = {route.assigned_agent_id for route in crisis.resource_routes_targeted.all() if route.assigned_agent_id}

    crisis_data = {
        'id': crisis.id,
        'name': crisis.name,
        'description': crisis.description,
        'status': crisis.status,
        'start_date': crisis.start_date.strftime('%Y-%m-%d'),
        'location_lat': crisis.location_lat,
        'location_lon': crisis.location_lon,
        'children_assigned_count': crisis.children_assigned.count(),
        'resources_targeted_count': crisis.resource_routes_targeted.count(),
        'agents_involved_count': len(involved_agent_ids),
        'children': children_in_crisis,
        'resources': resources_for_crisis
    }
    return jsonify(crisis_data)

# New Route for Donor Insights (for Mission Manager)
@app.route('/donor_insights')
@login_required
@role_required('mission_manager')
def donor_insights():
    # Fetch all users with the 'donor' role
    donors = User.query.filter_by(role='donor').all()
    
    # Fetch all donations to process insights
    all_donations_query = Donation.query.order_by(Donation.timestamp.asc()).all()

    # --- Prepare data for charts --- 
    # 1. Overall Donation Trend (similar to project_detail, but for all donations)
    overall_donation_timestamps = []
    overall_cumulative_donations = []
    current_overall_cumulative = Decimal('0.00')
    for don in all_donations_query:
        overall_donation_timestamps.append(don.timestamp.strftime('%Y-%m-%d'))
        current_overall_cumulative += Decimal(str(don.donation_size))
        overall_cumulative_donations.append(float(current_overall_cumulative))

    # 2. Donations by Project (Overall)
    donations_by_project_overall = {}
    for don in all_donations_query:
        if don.project_id and don.project:
            project_name = don.project.name
            donations_by_project_overall[project_name] = donations_by_project_overall.get(project_name, Decimal('0.00')) + Decimal(str(don.donation_size))
        elif not don.project_id:
             donations_by_project_overall["General Aid (Unassigned)"] = donations_by_project_overall.get("General Aid (Unassigned)", Decimal('0.00')) + Decimal(str(don.donation_size))

    overall_project_labels = list(donations_by_project_overall.keys())
    overall_project_values = [float(val) for val in donations_by_project_overall.values()]

    # 3. Top Donors (by total amount donated)
    top_donors_data = {}
    for donor_user in donors:
        donor_total = db.session.query(func.sum(Donation.donation_size)).filter_by(donor_id=donor_user.id).scalar()
        if donor_total and Decimal(str(donor_total)) > 0:
            top_donors_data[donor_user.username] = Decimal(str(donor_total))
    
    # Sort donors by amount and get top N (e.g., top 10)
    sorted_top_donors = sorted(top_donors_data.items(), key=lambda item: item[1], reverse=True)[:10]
    top_donor_labels = [item[0] for item in sorted_top_donors]
    top_donor_values = [float(item[1]) for item in sorted_top_donors]

    # --- Prepare data for donor table ---
    donor_table_data = []
    for d_user in donors:
        donations = Donation.query.filter_by(donor_id=d_user.id).all()
        total_donated = sum(Decimal(str(d.donation_size)) for d in donations)
        num_donations = len(donations)
        last_donation_date = max(d.timestamp for d in donations) if donations else None
        donor_table_data.append({
            'username': d_user.username,
            'total_donated': float(total_donated),
            'num_donations': num_donations,
            'last_donation_date': last_donation_date.strftime('%Y-%m-%d') if last_donation_date else 'N/A'
        })

    return render_template('donor_insights.html',
                           donors=donor_table_data,
                           overall_donation_timestamps=overall_donation_timestamps,
                           overall_cumulative_donations=overall_cumulative_donations,
                           overall_project_labels=overall_project_labels,
                           overall_project_values=overall_project_values,
                           top_donor_labels=top_donor_labels,
                           top_donor_values=top_donor_values
                           )

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

