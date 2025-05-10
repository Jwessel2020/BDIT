# models.py
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime # Ensure datetime is imported

db = SQLAlchemy()

class User(db.Model, UserMixin):
    """
    Basic User model for authentication and role-based permissions.
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # e.g., "field_agent", "donor", "child_care", "mission_manager"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# New Project Model
class Project(db.Model):
    __tablename__ = 'project'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    manager_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    budget = db.Column(db.Numeric(10, 2), nullable=True)
    start_date = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), nullable=True, default='Planning') # e.g., "Planning", "Ongoing", "Completed", "On Hold"
    
    goal_description = db.Column(db.Text, nullable=True)
    goal_target_value = db.Column(db.Numeric(10, 2), nullable=True)
    goal_current_value = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    goal_unit = db.Column(db.String(50), nullable=True) # e.g., "%", "children", "kg"

    manager = db.relationship('User', backref=db.backref('managed_projects', lazy='dynamic'))

    def __repr__(self):
        return f'<Project {self.id} - {self.name}>'

class Donation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    origin_lat = db.Column(db.Float, nullable=False)
    origin_lon = db.Column(db.Float, nullable=False)
    destination_lat = db.Column(db.Float, nullable=False)
    destination_lon = db.Column(db.Float, nullable=False)
    donation_size = db.Column(db.Float, nullable=False)
    donation_need = db.Column(db.String(255), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True) # Added
    project = db.relationship('Project', backref=db.backref('donations', lazy='dynamic')) # Added

    def __repr__(self):
        return f"<Donation {self.id}>"

class ResourceRoute(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    origin_lat = db.Column(db.Float, nullable=False)
    origin_lon = db.Column(db.Float, nullable=False)
    destination_lat = db.Column(db.Float, nullable=False)
    destination_lon = db.Column(db.Float, nullable=False)
    resource_type = db.Column(db.String(50), nullable=False)  # e.g., "Medical", "Food", etc.
    supply_quantity = db.Column(db.Integer, nullable=True)    # Optional field
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True) # Added
    project = db.relationship('Project', backref=db.backref('resource_routes', lazy='dynamic')) # Added

class ChildLocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True) # Added
    project = db.relationship('Project', backref=db.backref('child_locations_in_project', lazy='dynamic')) # Added

class FieldAgentLocation(db.Model):
    """
    Tracks current location of field agents.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True) # Added (e.g. location ping during a project-specific task)
    
    user = db.relationship('User', backref='locations')
    project = db.relationship('Project', backref=db.backref('field_agent_locations_in_project', lazy='dynamic')) # Added
    
    def __repr__(self):
        return f"<FieldAgentLocation id={self.id} user_id={self.user_id}>"

class ChildProfile(db.Model):
    """
    Stores information about a child in care.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    health_status = db.Column(db.String(255), nullable=False)  # e.g., "Healthy", "Under Observation", "Needs Attention"
    priority = db.Column(db.String(50), nullable=True)         # e.g., "High", "Medium", "Low"
    notes = db.Column(db.Text, nullable=True)
    # Current location data for the child - might be better in a separate ChildCurrentLocation table if it changes often
    current_lat = db.Column(db.Float, nullable=True)
    current_lon = db.Column(db.Float, nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True) # Added
    project = db.relationship('Project', backref=db.backref('child_profiles', lazy='dynamic')) # Added

class Message(db.Model):
    """
    Stores messages for the messaging system.
    """
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # For one-to-one messaging, you can have a recipient_id.
    # For group chat or channels, you might store a channel name instead.
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    channel = db.Column(db.String(50), nullable=True)  # For group messages.
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    priority = db.Column(db.String(20), nullable=True)  # Optional: "High", "Medium", "Low"
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True) # Added (e.g. messages in a project-specific channel)
    
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')
    project = db.relationship('Project', backref=db.backref('messages', lazy='dynamic')) # Added

    def __repr__(self):
        return f"<Message {self.id} from {self.sender_id}>"
