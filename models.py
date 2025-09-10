from app import db
from datetime import datetime
from sqlalchemy import Text, Boolean, String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column


class Conversation(db.Model):
    """Model for tracking SMS conversations"""
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone_number: Mapped[str] = mapped_column(String(20),
                                              nullable=False,
                                              index=True)

    # Conversation metadata
    created_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=datetime.utcnow,
                                                 nullable=False)
    last_activity: Mapped[datetime] = mapped_column(DateTime,
                                                    default=datetime.utcnow,
                                                    nullable=False)

    # Escalation tracking
    needs_human_attention: Mapped[bool] = mapped_column(Boolean,
                                                        default=False,
                                                        nullable=False)
    escalation_reason: Mapped[str] = mapped_column(Text, nullable=True)
    escalated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Conversation context and notes
    context_summary: Mapped[str] = mapped_column(
        Text, nullable=True)  # AI-generated summary of conversation
    client_notes: Mapped[str] = mapped_column(
        Text, nullable=True)  # Any special notes about the client

    # Privacy and consent
    consent_given: Mapped[bool] = mapped_column(Boolean,
                                                default=False,
                                                nullable=False)

    # Relationship to messages
    messages = relationship("Message",
                            back_populates="conversation",
                            cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Conversation {self.id}: {self.phone_number}>'

    def get_last_messages(self, limit=5):
        """Get the last N messages for context"""
        return Message.query.filter_by(conversation_id=self.id).order_by(
            Message.timestamp.desc()).limit(limit).all()

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()


class Message(db.Model):
    """Model for individual SMS messages"""
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(Integer,
                                                 ForeignKey('conversation.id'),
                                                 nullable=False)

    # Message content
    message_body: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(
        String(20), nullable=False)  # 'incoming' or 'outgoing'

    # Timestamps
    timestamp: Mapped[datetime] = mapped_column(DateTime,
                                                default=datetime.utcnow,
                                                nullable=False)

    # Twilio metadata (changed from SignalWire)
    twilio_message_sid: Mapped[str] = mapped_column(String(100), nullable=True)
    from_number: Mapped[str] = mapped_column(String(20), nullable=True)
    to_number: Mapped[str] = mapped_column(String(20), nullable=True)

    # AI processing metadata
    ai_model_used: Mapped[str] = mapped_column(String(50), nullable=True)
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    confidence_score: Mapped[float] = mapped_column(db.Float, nullable=True)

    # Flags for special handling
    contains_urgent_keywords: Mapped[bool] = mapped_column(Boolean,
                                                           default=False)
    contains_medical_request: Mapped[bool] = mapped_column(Boolean,
                                                           default=False)

    # Relationship back to conversation
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f'<Message {self.id}: {self.message_type} at {self.timestamp}>'


class EscalationLog(db.Model):
    """Log of conversations that needed human intervention"""
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(Integer,
                                                 ForeignKey('conversation.id'),
                                                 nullable=False)

    reason: Mapped[str] = mapped_column(String(100), nullable=False)
    escalated_at: Mapped[datetime] = mapped_column(DateTime,
                                                   default=datetime.utcnow,
                                                   nullable=False)
    resolved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Human doula notes
    doula_notes: Mapped[str] = mapped_column(Text, nullable=True)
    resolution_summary: Mapped[str] = mapped_column(Text, nullable=True)

    def __repr__(self):
        return f'<EscalationLog {self.id}: {self.reason}>'
