from flask import request
from flask_socketio import emit, join_room, leave_room
from flask_login import current_user
from models import db, User, Message # Assuming models.py is in parent dir and accessible
from datetime import datetime

def register_socket_events(socketio):
    """Register all socket event handlers with the given socketio instance."""

    @socketio.on('connect')
    def on_connect():
        """Handle new client connections."""
        if current_user.is_authenticated:
            # Automatically join a room named after the user_id for direct messages
            join_room(str(current_user.id))
            print(f"User {current_user.username} (ID: {current_user.id}) connected and joined room {current_user.id}.")
        else:
            print("Anonymous user connected.")

    @socketio.on('disconnect')
    def on_disconnect():
        """Handle client disconnections."""
        if current_user.is_authenticated:
            # Leave the room named after the user_id
            leave_room(str(current_user.id))
            print(f"User {current_user.username} (ID: {current_user.id}) disconnected and left room {current_user.id}.")
        else:
            print("Anonymous user disconnected.")

    @socketio.on('join_channel')
    def on_join_channel(data):
        """Allows a user to join a specific channel/room."""
        if not current_user.is_authenticated:
            return # Or emit an error
        
        channel = data.get('channel')
        if channel:
            join_room(channel)
            print(f"User {current_user.username} joined channel: {channel}")
            emit('status', {'msg': f'{current_user.username} has entered the channel {channel}.'}, room=channel)
        else:
            print(f"User {current_user.username} attempted to join a null channel.")

    @socketio.on('leave_channel')
    def on_leave_channel(data):
        """Allows a user to leave a specific channel/room."""
        if not current_user.is_authenticated:
            return

        channel = data.get('channel')
        if channel:
            leave_room(channel)
            print(f"User {current_user.username} left channel: {channel}")
            emit('status', {'msg': f'{current_user.username} has left the channel {channel}.'}, room=channel)

    @socketio.on('send_message')
    def handle_send_message(data):
        """
        Handles receiving a message from a client and broadcasting it.
        Expected data format:
        {
            'content': 'Hello!', 
            'recipient_id': 'user_id_if_direct_message',  // Optional
            'channel': 'channel_name_if_group_message', // Optional
            'project_id': 'project_id_if_related_to_project' // Optional
        }
        The sender_id is derived from current_user.
        """
        if not current_user.is_authenticated:
            emit('error', {'message': 'Authentication required to send messages.'})
            return

        content = data.get('content')
        recipient_id = data.get('recipient_id')
        channel = data.get('channel')
        project_id = data.get('project_id') # Get project_id if provided

        if not content:
            emit('error', {'message': 'Message content cannot be empty.'})
            return
        
        if not recipient_id and not channel:
            emit('error', {'message': 'Message must have a recipient or a channel.'})
            return

        try:
            message = Message(
                sender_id=current_user.id,
                recipient_id=int(recipient_id) if recipient_id else None,
                channel=channel,
                content=content,
                project_id=int(project_id) if project_id else None, # Save project_id
                timestamp=datetime.utcnow(), # Use UTC for consistency
                priority=data.get('priority', 'Normal') # Optional priority
            )
            db.session.add(message)
            db.session.commit()

            emit_data = {
                'id': message.id,
                'sender_id': current_user.id,
                'sender_name': current_user.username,
                'content': message.content,
                'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'),
                'priority': message.priority,
                'channel': message.channel, # Include channel in emit if it exists
                'project_id': message.project_id # Include project_id in emit if it exists
            }

            if channel: # Message for a channel (group)
                print(f"Broadcasting message to channel {channel}: {emit_data}")
                emit('receive_message', emit_data, room=channel)
            elif recipient_id: # Direct message
                # Send to recipient's room (named by their ID)
                print(f"Sending direct message to user {recipient_id}: {emit_data}")
                emit('receive_message', emit_data, room=str(recipient_id))
                # Also send to sender's room so they see their own message
                emit('receive_message', emit_data, room=str(current_user.id))

        except Exception as e:
            db.session.rollback() # Rollback in case of error during DB operations
            print(f"Error sending message: {e}")
            emit('error', {'message': f'An error occurred: {str(e)}'})

    # You can add more socket event handlers here as needed
    print("SocketIO events registered from messaging.socket_events")
