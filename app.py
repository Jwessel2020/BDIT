# app.py
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, abort
import random
from models import db, Donation, User, ResourceRoute, ChildLocation, ChildProfile, Message, FieldAgentLocation
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from functools import wraps
from datetime import datetime
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ngo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'supersecretkey'  # Replace with a secure key
db.init_app(app)

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
                return abort(403)
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper

#####################################
# Routes for Authentication
#####################################
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        print(f"Attempting login for {username}")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
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
def index():
    if current_user.is_authenticated:
        return render_template('index.html')
    else:
        return redirect(url_for('login'))

@app.route('/field_agent')
@login_required
@role_required('field_agent', 'mission_manager')
def field_agent():
    # Get the latest location for this agent, or create a default if none exists
    agent_location = FieldAgentLocation.query.filter_by(user_id=current_user.id).order_by(FieldAgentLocation.timestamp.desc()).first()
    
    if not agent_location:
        # Default to a location in South Africa if no location exists yet
        gps_data = {
            "latitude": -30.5595,
            "longitude": 22.9375
        }
    else:
        gps_data = {
            "latitude": agent_location.lat,
            "longitude": agent_location.lon
        }
    
    # In a real app, you might fetch real messages for this user
    messages = []  # This would be replaced with real message data
    
    return render_template('field_agent.html', gps_data=gps_data, messages=messages)

@app.route('/update_location', methods=['POST'])
@login_required
@role_required('field_agent', 'mission_manager')
def update_location():
    try:
        # In a real app, you'd get this from a GPS system
        # For demo purposes, we'll generate a random location in South Africa
        # Actual coords would come from the request
        
        # If you want to test with specific coordinates, you could uncomment these lines
        # lat = request.form.get('lat')
        # lon = request.form.get('lon')
        
        # For demo, we'll use random coordinates around South Africa
        lat = round(random.uniform(-35, -22), 6)  # South Africa latitude range
        lon = round(random.uniform(16, 33), 6)    # South Africa longitude range
        
        # Create a new location entry
        new_location = FieldAgentLocation(
            user_id=current_user.id,
            lat=lat,
            lon=lon,
            timestamp=datetime.now()
        )
        
        db.session.add(new_location)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "latitude": lat,
            "longitude": lon,
            "message": "Location updated successfully"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error updating location: {str(e)}"
        }), 500

@app.route('/donor')
@login_required
@role_required('donor', 'mission_manager')
def donor():
    donation_stats = {
        'total_donations': 15000,
        'projects_supported': 5,
        'impact_score': 87,
        'currency_trace': "USD → ZAR @ 15.2"
    }
    return render_template('donor.html', donation_stats=donation_stats)

# Updated Child Care route using ChildProfile model
@app.route('/child_care')
@login_required
@role_required('child_care', 'mission_manager')
def child_care():
    child_profiles = ChildProfile.query.all()
    return render_template('child_care.html', child_profiles=child_profiles)

# Add Child Profile route
@app.route('/add_child_profile', methods=['GET', 'POST'])
@login_required
@role_required('child_care', 'mission_manager')
def add_child_profile():
    if request.method == 'POST':
        name = request.form.get('name')
        age = request.form.get('age')
        health_status = request.form.get('health_status')
        priority = request.form.get('priority')
        notes = request.form.get('notes')
        
        if name and age:
            new_profile = ChildProfile(
                name=name,
                age=int(age),
                health_status=health_status,
                priority=priority,
                notes=notes
            )
            db.session.add(new_profile)
            db.session.commit()
            flash('Child profile added successfully!', 'success')
            return redirect(url_for('child_care'))
        
        flash('Name and age are required!', 'danger')
        
    return render_template('add_child_profile.html')

# Unified Map Route (includes donation heatmap integrated)
@app.route('/map')
@login_required
@role_required('field_agent', 'child_care', 'donor', 'mission_manager')
def map_view():
    fund_tracing = {
        "origin": {"lat": -33.9249, "lon": 18.4241, "name": "Cape Town"},
        "destination": {"lat": -29.8587, "lon": 31.0218, "name": "Durban"},
        "donation_size": 5000,
        "donation_need": "Medical Supplies"
    }
    resource_routes_db = ResourceRoute.query.all()
    resource_routes = []
    for route in resource_routes_db:
        resource_routes.append({
            "origin": {"lat": route.origin_lat, "lon": route.origin_lon},
            "destination": {"lat": route.destination_lat, "lon": route.destination_lon},
            "resource_type": route.resource_type,
        })
    child_locations_db = ChildLocation.query.all()
    child_locations = []
    for child in child_locations_db:
        child_locations.append({
            "lat": child.lat,
            "lon": child.lon,
            "name": child.name
        })
        
    # Get field agent locations
    field_agent_locations_db = FieldAgentLocation.query.order_by(
        FieldAgentLocation.user_id, FieldAgentLocation.timestamp.desc()
    ).all()
    
    # Dictionary to track the most recent location for each agent
    latest_locations = {}
    field_agent_locations = []
    
    for loc in field_agent_locations_db:
        # Only add the most recent location for each agent
        if loc.user_id not in latest_locations:
            agent = User.query.get(loc.user_id)
            latest_locations[loc.user_id] = True
            field_agent_locations.append({
                "lat": loc.lat,
                "lon": loc.lon,
                "name": agent.username if agent else f"Agent {loc.user_id}",
                "timestamp": loc.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            })
    
    donations = Donation.query.all()
    donation_routes = []
    heat_data = []  # For donation heatmap
    for d in donations:
        donation_routes.append({
            "origin": {"lat": d.origin_lat, "lon": d.origin_lon},
            "destination": {"lat": d.destination_lat, "lon": d.destination_lon},
            "donation_size": d.donation_size,
            "donation_need": d.donation_need
        })
        heat_data.append([d.destination_lat, d.destination_lon, d.donation_size])
    return render_template("map.html",
                           fund_tracing=fund_tracing,
                           resource_routes=resource_routes,
                           child_locations=child_locations,
                           donation_routes=donation_routes,
                           field_agent_locations=field_agent_locations,
                           heat_data=heat_data)

@app.route('/manager_dashboard')
@login_required
@role_required('mission_manager')
def manager_dashboard():
    return render_template('manager_dashboard.html')

# QR Code Scanner Route Example
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

from flask_socketio import SocketIO, join_room, leave_room, emit

# After app initialization:
socketio = SocketIO(app)

# A simple event handler for receiving messages:
@socketio.on('send_message')
def handle_send_message(data):
    """
    Expected data: {
      'sender_id': <sender_id>,
      'recipient_id': <recipient_id>,  # optional for one-to-one
      'channel': <channel>,            # optional for group chat
      'content': <message content>,
      'priority': <optional priority>
    }
    """
    # Save the message to the database
    sender_id = data.get('sender_id')
    recipient_id = data.get('recipient_id')
    channel = data.get('channel')
    content = data.get('content')
    priority = data.get('priority', 'Normal')
    
    message = Message(
        sender_id=sender_id,
        recipient_id=recipient_id,
        channel=channel,
        content=content,
        priority=priority,
        timestamp=datetime.now()
    )
    db.session.add(message)
    db.session.commit()
    
    # Emit the message to appropriate recipients
    if channel:
        # Group message, send to the channel
        emit('receive_message', {
            'id': message.id,
            'sender_id': message.sender_id,
            'sender_name': User.query.get(sender_id).username,
            'content': message.content,
            'timestamp': message.timestamp.strftime('%H:%M'),
            'priority': message.priority
        }, room=channel)
    elif recipient_id:
        # Direct message, send to both sender and recipient
        for user_id in [sender_id, recipient_id]:
            emit('receive_message', {
                'id': message.id,
                'sender_id': message.sender_id,
                'sender_name': User.query.get(sender_id).username,
                'content': message.content,
                'timestamp': message.timestamp.strftime('%H:%M'),
                'priority': message.priority
            }, room=str(user_id))
            
# Route for chat functionality
@app.route('/chat')
@login_required
def chat():
    # Get the list of users to chat with
    users = User.query.filter(User.id != current_user.id).all()
    
    # Get channels/groups
    channels = ["Emergency Response Team", "Resource Management", "Field Operations"]
    
    # Get recent messages for the user
    received_messages = Message.query.filter(
        (Message.recipient_id == current_user.id) | 
        (Message.channel.in_(channels))
    ).order_by(Message.timestamp.desc()).limit(20).all()
    
    sent_messages = Message.query.filter_by(
        sender_id=current_user.id
    ).order_by(Message.timestamp.desc()).limit(20).all()
    
    # Combine and sort messages by timestamp
    messages = sorted(
        list(received_messages) + list(sent_messages),
        key=lambda x: x.timestamp,
        reverse=True
    )[:20]  # Get the 20 most recent messages
    
    return render_template('chat.html', users=users, channels=channels, messages=messages)

# Connect user to their personal room when they connect
@socketio.on('connect')
def on_connect():
    join_room(str(current_user.id))
    print(f"User {current_user.username} connected")
    
# Have user join a channel room
@socketio.on('join_channel')
def on_join_channel(data):
    channel = data['channel']
    join_room(channel)
    print(f"User {current_user.username} joined channel {channel}")
    
# Disconnect from personal room when they disconnect
@socketio.on('disconnect')
def on_disconnect():
    print(f"User {current_user.username} disconnected")

# Import CLI commands to register them
import cli  # noqa

# Add this after app initialization to run with SocketIO
if __name__ == '__main__':
    socketio.run(app, debug=True)

