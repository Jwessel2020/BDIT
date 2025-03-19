# models.py
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

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

class Donation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    origin_lat = db.Column(db.Float, nullable=False)
    origin_lon = db.Column(db.Float, nullable=False)
    destination_lat = db.Column(db.Float, nullable=False)
    destination_lon = db.Column(db.Float, nullable=False)
    donation_size = db.Column(db.Float, nullable=False)
    donation_need = db.Column(db.String(255), nullable=False)

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

class ChildLocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    name = db.Column(db.String(100), nullable=False)

class FieldAgentLocation(db.Model):
    """
    Tracks current location of field agents.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    user = db.relationship('User', backref='locations')
    
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
    
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')

    def __repr__(self):
        return f"<Message {self.id} from {self.sender_id}>"
