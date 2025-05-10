from flask import render_template
from flask_login import login_required, current_user
from . import messaging_bp # Import the blueprint instance

@messaging_bp.route('/chat')
@login_required
def chat():
    """Main chat page route."""
    # You can pass any necessary data to the chat template here
    # For example, a list of channels or recent messages, though much
    # of the dynamic content might be handled by SocketIO on the client-side.
    return render_template('chat.html', current_user=current_user)
