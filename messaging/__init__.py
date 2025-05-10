from flask import Blueprint

# Create a Blueprint for the messaging functionality
messaging_bp = Blueprint('messaging', __name__, template_folder='templates') # Added template_folder if you have chat.html in messaging/templates

# Import routes and socket events to register them with the blueprint
# These imports need to be after messaging_bp is defined to avoid circular dependencies if they import messaging_bp
from . import routes
from . import socket_events # Assuming socket_events.py contains register_socket_events

# Function to initialize the messaging system with the app and socketio
def init_messaging(app, socketio):
    """Initializes the messaging blueprint and registers socket events."""
    app.register_blueprint(messaging_bp, url_prefix='/messaging') # Added a URL prefix for clarity
    
    # Check if register_socket_events is available and call it
    if hasattr(socket_events, 'register_socket_events'):
        socket_events.register_socket_events(socketio) # Pass the main socketio instance
    else:
        # Handle the case where the function might not be found, e.g., log a warning
        app.logger.warning("register_socket_events not found in messaging.socket_events")
