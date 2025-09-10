import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Set up logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///doula_sms.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

with app.app_context():
    # Import models to ensure tables are created
    import models  # noqa: F401
    db.create_all()

# Import and register blueprints
from webhook import webhook_bp
from flask import render_template, request, jsonify
from models import Conversation, Message
from datetime import datetime, timedelta

app.register_blueprint(webhook_bp)

@app.route('/')
def index():
    """Dashboard showing recent activity and system status"""
    # Get recent conversations
    recent_conversations = Conversation.query.order_by(
        Conversation.last_activity.desc()
    ).limit(10).all()
    
    # Get stats
    total_conversations = Conversation.query.count()
    today = datetime.utcnow().date()
    today_conversations = Conversation.query.filter(
        db.func.date(Conversation.created_at) == today
    ).count()
    
    # Get messages from last 24 hours
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_messages = Message.query.filter(
        Message.timestamp >= yesterday
    ).count()
    
    stats = {
        'total_conversations': total_conversations,
        'today_conversations': today_conversations,
        'recent_messages': recent_messages,
        'active_conversations': Conversation.query.filter(
            Conversation.last_activity >= yesterday
        ).count()
    }
    
    return render_template('index.html', 
                         conversations=recent_conversations,
                         stats=stats)

@app.route('/conversations')
def conversations():
    """View all conversations with pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    conversations = Conversation.query.order_by(
        Conversation.last_activity.desc()
    ).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('conversations.html', conversations=conversations)

@app.route('/conversation/<int:conversation_id>')
def conversation_detail(conversation_id):
    """View detailed conversation with all messages"""
    conversation = Conversation.query.get_or_404(conversation_id)
    messages = Message.query.filter_by(
        conversation_id=conversation_id
    ).order_by(Message.timestamp.asc()).all()
    
    return render_template('conversation_detail.html', 
                         conversation=conversation,
                         messages=messages)

@app.route('/debug')
def debug_status():
    """Debug status page showing system health and configuration"""
    # Import SignalWire client from webhook module
    from webhook import signalwire_client
    
    # Get environment variables (without exposing sensitive data)
    signalwire_configured = bool(os.environ.get('SIGNALWIRE_PROJECT_ID')) and bool(os.environ.get('SIGNALWIRE_AUTH_TOKEN')) and bool(os.environ.get('SIGNALWIRE_SPACE_URL'))
    phone_number_configured = bool(os.environ.get('SIGNALWIRE_PHONE_NUMBER'))
    
    # Get database stats
    try:
        total_conversations = Conversation.query.count()
        total_messages = Message.query.count()
        today = datetime.utcnow().date()
        today_conversations = Conversation.query.filter(
            db.func.date(Conversation.created_at) == today
        ).count()
        
        # Get recent activity
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_messages = Message.query.filter(
            Message.timestamp >= yesterday
        ).count()
        
        active_conversations = Conversation.query.filter(
            Conversation.last_activity >= yesterday
        ).count()
        
        escalated_conversations = Conversation.query.filter(
            Conversation.needs_human_attention == True
        ).count()
        
        db_status = 'connected'
        db_error = None
    except Exception as e:
        total_conversations = 0
        total_messages = 0
        today_conversations = 0
        recent_messages = 0
        active_conversations = 0
        escalated_conversations = 0
        db_status = 'error'
        db_error = str(e)
    
    debug_info = {
        'timestamp': datetime.utcnow(),
        'environment': {
            'signalwire_client_initialized': signalwire_client is not None,
            'signalwire_credentials_configured': signalwire_configured,
            'signalwire_phone_number_configured': phone_number_configured,
            'database_status': db_status,
            'database_error': db_error
        },
        'stats': {
            'total_conversations': total_conversations,
            'total_messages': total_messages,
            'today_conversations': today_conversations,
            'recent_messages_24h': recent_messages,
            'active_conversations_24h': active_conversations,
            'escalated_conversations': escalated_conversations
        },
        'endpoints': {
            'sms_webhook': '/webhook/sms',
            'webhook_status_api': '/webhook/status',
            'test_sms': '/webhook/test',
            'debug_page': '/debug'
        }
    }
    
    return render_template('debug.html', debug_info=debug_info)

@app.route('/debug/logs')
def debug_logs():
    """Get recent application logs"""
    try:
        # Get recent log entries from the application logger
        import logging
        import io
        
        # Create a custom log handler to capture recent logs
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        # Get the root logger and check for recent entries
        logger = logging.getLogger()
        
        # Since we can't easily retrieve historical logs, return recent activity from database
        from datetime import timedelta
        recent_time = datetime.utcnow() - timedelta(minutes=30)
        
        # Get recent messages as a proxy for activity
        recent_messages = Message.query.filter(
            Message.timestamp >= recent_time
        ).order_by(Message.timestamp.desc()).limit(20).all()
        
        logs = []
        for msg in recent_messages:
            log_entry = {
                'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'level': 'INFO',
                'message': f"SMS {msg.message_type} - {msg.from_number}: {msg.message_body[:50]}..."
            }
            logs.append(log_entry)
        
        return {'logs': logs}
    except Exception as e:
        return {'logs': [{'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), 'level': 'ERROR', 'message': f'Error retrieving logs: {str(e)}'}]}

@app.route('/api/escalate/<int:conversation_id>', methods=['POST'])
def escalate_conversation(conversation_id):
    """Mark conversation for human escalation"""
    conversation = Conversation.query.get_or_404(conversation_id)
    conversation.needs_human_attention = True
    data = request.get_json() or {}
    conversation.escalation_reason = data.get('reason', 'Manual escalation')
    db.session.commit()
    
    return jsonify({'status': 'success', 'message': 'Conversation escalated'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
