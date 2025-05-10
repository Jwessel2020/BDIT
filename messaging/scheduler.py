import threading
import time
from datetime import datetime, timedelta
from models import db, Message, User # Assuming models.py is in the parent directory and accessible

class MessageScheduler:
    """
    Handles scheduling and sending automated messages.
    This class will run in a separate thread and periodically check for messages
    that need to be sent based on their scheduled time.
    """
    def __init__(self, socketio, app_context):
        self.socketio = socketio
        self.app_context = app_context # Needed for database operations in a separate thread
        self.scheduler_thread = None
        self.running = False
        self.scheduled_messages = [] # This will store dicts of message data and send_time

    def start(self):
        """Start the scheduler thread if it's not already running."""
        if self.scheduler_thread and self.running:
            print("Scheduler is already running.")
            return False
        
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop)
        self.scheduler_thread.daemon = True # Daemon threads exit when the main program exits
        self.scheduler_thread.start()
        print("Message scheduler started.")
        return True

    def stop(self):
        """Stop the scheduler thread gracefully."""
        print("Attempting to stop message scheduler...")
        self.running = False
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5.0) # Wait for the thread to finish
            if self.scheduler_thread.is_alive():
                print("Scheduler thread did not stop in time.")
            else:
                print("Message scheduler stopped.")
        else:
            print("Scheduler thread was not running or already stopped.")
        self.scheduler_thread = None

    def _scheduler_loop(self):
        """Main loop for the scheduler thread. Checks and sends messages."""
        print("Scheduler loop started.")
        while self.running:
            now = datetime.utcnow() # Use UTC for consistency
            messages_to_send_now = []
            
            # Lock could be used here if self.scheduled_messages is modified elsewhere frequently
            # For simplicity, assuming modifications are primarily via schedule_message
            for i in range(len(self.scheduled_messages) - 1, -1, -1): # Iterate backwards for safe removal
                msg_data = self.scheduled_messages[i]
                if now >= msg_data['send_time']:
                    messages_to_send_now.append(msg_data)
                    del self.scheduled_messages[i] # Remove from schedule
            
            if messages_to_send_now:
                with self.app_context(): # Ensure DB operations happen within app context
                    for msg_data in messages_to_send_now:
                        self._send_scheduled_message(msg_data)
            
            time.sleep(5) # Check every 5 seconds
        print("Scheduler loop ended.")

    def _send_scheduled_message(self, msg_data):
        """Sends a single scheduled message using SocketIO and saves it to DB."""
        print(f"Sending scheduled message: {msg_data['content']}")
        try:
            # Create and save the message to the database
            message = Message(
                sender_id=msg_data['sender_id'],
                recipient_id=msg_data.get('recipient_id'),
                channel=msg_data.get('channel'),
                content=msg_data['content'],
                priority=msg_data.get('priority', 'Normal'),
                timestamp=datetime.utcnow() # Use UTC for timestamp
            )
            db.session.add(message)
            db.session.commit()

            sender_user = User.query.get(msg_data['sender_id'])
            sender_name = sender_user.username if sender_user else "System"

            emit_data = {
                'id': message.id,
                'sender_id': message.sender_id,
                'sender_name': sender_name,
                'content': message.content,
                'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'),
                'priority': message.priority,
                'scheduled': True
            }

            # Emit the message via SocketIO
            if message.channel:
                self.socketio.emit('receive_message', emit_data, room=message.channel)
            elif message.recipient_id:
                # For direct messages, ensure the recipient is also in a room named by their ID
                self.socketio.emit('receive_message', emit_data, room=str(message.recipient_id))
                # Optionally, also send to sender's room if they should see their own scheduled messages
                self.socketio.emit('receive_message', emit_data, room=str(message.sender_id))
            
            print(f"Scheduled message ID {message.id} sent and saved.")

        except Exception as e:
            print(f"Error sending scheduled message: {e}")
            # Optionally, re-queue the message or log to a persistent error log
            # For now, we'll just print the error

    def schedule_message(self, sender_id, content, send_time_utc=None, delay_minutes=None, 
                        recipient_id=None, channel=None, priority='Normal'):
        """
        Schedules a message to be sent at a specific UTC time or after a delay.
        
        Args:
            sender_id: ID of the sending user.
            content: Message content.
            send_time_utc: UTC datetime when the message should be sent.
            delay_minutes: Alternative to send_time_utc, minutes from now to send.
            recipient_id: ID of the recipient user for direct messages.
            channel: Channel name for group messages.
            priority: Message priority (Normal, High, Emergency).
        """
        if not send_time_utc and delay_minutes is not None:
            send_time_utc = datetime.utcnow() + timedelta(minutes=delay_minutes)
        elif not send_time_utc:
            # Default to sending immediately if no time/delay specified, though usually an explicit time is better.
            send_time_utc = datetime.utcnow()
            
        if not isinstance(send_time_utc, datetime):
            print("Error: send_time_utc must be a datetime object.")
            return False
            
        scheduled_msg = {
            'sender_id': sender_id,
            'content': content,
            'send_time': send_time_utc, # Ensure this is a datetime object
            'priority': priority
        }
        
        if recipient_id:
            scheduled_msg['recipient_id'] = recipient_id
        elif channel:
            scheduled_msg['channel'] = channel
        else:
            print("Error: Message must have a recipient_id or a channel.")
            return False
        
        # Add to sorted list (optional, simple append and sort later is also fine for moderate numbers)
        self.scheduled_messages.append(scheduled_msg)
        # self.scheduled_messages.sort(key=lambda x: x['send_time']) # Keep sorted if many messages
        
        print(f"Message scheduled for {send_time_utc}. Queue size: {len(self.scheduled_messages)}")
        return True
