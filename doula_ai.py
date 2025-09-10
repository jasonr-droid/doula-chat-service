import os
import logging
import time
import re
from typing import Dict, List, Optional, Tuple

# Simple doula AI service without external dependencies
class SimpleDoulaAI:
    """Simple rule-based doula support system with keyword matching"""
    
    def __init__(self):
        self.urgent_keywords = [
            'emergency', 'urgent', 'help', 'crisis', 'suicide', 'kill myself',
            'abuse', 'violence', 'pain', 'bleeding', 'can\'t breathe',
            'chest pain', 'stroke', 'heart attack', 'overdose', 'poison',
            '911', 'hospital', 'dying', 'dying now'
        ]
        
        self.medical_keywords = [
            'doctor', 'medicine', 'medication', 'diagnosis', 'treatment',
            'prescription', 'dosage', 'symptoms', 'medical advice',
            'should I take', 'is this normal medically', 'nurse',
            'surgery', 'operation'
        ]
        
        # Pre-defined compassionate responses for common situations
        self.response_templates = {
            'greeting': [
                "Hello, I'm here to support you during this difficult time. How can I help you today?",
                "Thank you for reaching out. I'm here to provide compassionate support. What's on your heart?",
                "I'm glad you contacted us. How can I offer comfort and guidance today?"
            ],
            'end_of_life': [
                "This is such a sacred time. Every person's journey is unique and there's no 'right' way to experience this.",
                "I'm here to support you through this transition. What questions or concerns do you have?",
                "These feelings are completely normal during end-of-life care. You're not alone in this."
            ],
            'fear_anxiety': [
                "Fear during this time is completely understandable. It's okay to feel scared and uncertain.",
                "Your feelings are valid. Many families experience these emotions during end-of-life care.",
                "Anxiety is a natural response. Take deep breaths. I'm here to support you through this."
            ],
            'family_support': [
                "Supporting a loved one through this journey takes tremendous strength. You're doing important work.",
                "Family dynamics can be complex during end-of-life care. It's okay to need support too.",
                "Being present for your loved one is a gift. How are you taking care of yourself as well?"
            ],
            'practical': [
                "Let's talk through the practical steps. What specific area would you like guidance with?",
                "I can help you think through the practical aspects while honoring your values and wishes.",
                "Planning ahead can bring peace of mind. What questions do you have about the process?"
            ],
            'grief': [
                "Grief is love with nowhere to go. Your feelings of loss are a testament to your love.",
                "There's no timeline for grief. Be patient and gentle with yourself during this process.",
                "Anticipatory grief is real and valid. Many people experience loss before death occurs."
            ],
            'default': [
                "I'm here to listen and support you. Can you tell me more about what you're experiencing?",
                "Thank you for sharing with me. How can I best support you right now?",
                "I hear you, and I'm here to help however I can. What feels most important to address?"
            ],
            'escalation': [
                "Thank you for reaching out. A doula will be with you shortly to provide the personal support you need.",
                "I want to make sure you get the best care possible. Katy will be in touch with you soon.",
                "You deserve personalized attention for this important matter. A human doula will contact you directly."
            ]
        }
    
    def analyze_message_urgency(self, message: str) -> Tuple[bool, List[str]]:
        """Analyze if message contains urgent keywords requiring escalation"""
        message_lower = message.lower()
        urgent_found = [kw for kw in self.urgent_keywords if kw in message_lower]
        medical_found = [kw for kw in self.medical_keywords if kw in message_lower]
        
        needs_escalation = len(urgent_found) > 0 or len(medical_found) > 0
        return needs_escalation, urgent_found + medical_found
    
    def categorize_message(self, message: str) -> str:
        """Categorize message to select appropriate response template"""
        message_lower = message.lower()
        
        # Greeting patterns
        if any(word in message_lower for word in ['hello', 'hi', 'hey', 'good morning', 'good afternoon']):
            return 'greeting'
        
        # End-of-life related
        if any(word in message_lower for word in ['dying', 'death', 'passing', 'end of life', 'terminal', 'hospice']):
            return 'end_of_life'
        
        # Fear and anxiety
        if any(word in message_lower for word in ['scared', 'afraid', 'anxious', 'worried', 'fear', 'terrified']):
            return 'fear_anxiety'
        
        # Family support
        if any(word in message_lower for word in ['family', 'spouse', 'husband', 'wife', 'children', 'mom', 'dad', 'mother', 'father']):
            return 'family_support'
        
        # Practical questions
        if any(word in message_lower for word in ['how', 'what should', 'when', 'planning', 'prepare', 'arrangements']):
            return 'practical'
        
        # Grief
        if any(word in message_lower for word in ['grief', 'sad', 'miss', 'loss', 'mourning', 'heartbroken']):
            return 'grief'
        
        return 'default'
    
    def build_context_string(self, recent_messages: List) -> str:
        """Build context string from recent conversation messages"""
        if not recent_messages:
            return "This is the start of a new conversation."
        
        context_parts = ["Recent conversation context:"]
        for msg in reversed(recent_messages[-3:]):  # Last 3 messages, oldest first
            role = "Client" if msg.message_type == "incoming" else "Assistant"
            context_parts.append(f"{role}: {msg.message_body}")
        
        return "\n".join(context_parts)
    
    def generate_response(self, message: str, conversation_context: str = "", 
                         phone_number: str = "") -> Dict:
        """Generate compassionate response using rule-based AI"""
        start_time = time.time()
        
        try:
            # Check for urgent keywords first
            needs_escalation, keywords = self.analyze_message_urgency(message)
            
            # Determine response category
            category = self.categorize_message(message)
            
            # Select appropriate response template
            if needs_escalation:
                response_text = self.response_templates['escalation'][0]
                escalation_reason = f"Urgent keywords detected: {', '.join(keywords)}"
            else:
                # Select a response from the category
                import random
                responses = self.response_templates.get(category, self.response_templates['default'])
                response_text = random.choice(responses)
                escalation_reason = None
            
            # Add context-aware personalization
            if 'thank you' in message.lower():
                response_text = "You're so welcome. " + response_text
            
            processing_time = int((time.time() - start_time) * 1000)
            
            return {
                'response': response_text,
                'should_escalate': needs_escalation,
                'escalation_reason': escalation_reason,
                'processing_time_ms': processing_time,
                'model_used': 'SimpleDoulaAI',
                'confidence_score': 0.75,  # Rule-based confidence
                'urgent_keywords': keywords if needs_escalation else [],
                'contains_medical_request': any('medic' in kw for kw in keywords),
                'message_category': category
            }
            
        except Exception as e:
            logging.error(f"Error generating AI response: {str(e)}")
            return {
                'response': "I'm here to support you, but I'm having technical difficulties right now. Please know that Katy Reyna will be notified and will reach out to you directly soon.",
                'should_escalate': True,
                'escalation_reason': f"AI system error: {str(e)}",
                'processing_time_ms': int((time.time() - start_time) * 1000),
                'model_used': 'SimpleDoulaAI',
                'confidence_score': 0.0,
                'urgent_keywords': [],
                'contains_medical_request': False,
                'message_category': 'error'
            }
    
    def generate_conversation_summary(self, messages: List) -> str:
        """Generate a summary of the conversation using keyword analysis"""
        if not messages:
            return "No messages in conversation yet."
        
        try:
            # Count message types and analyze patterns
            client_messages = [msg for msg in messages if msg.message_type == "incoming"]
            
            if not client_messages:
                return "No client messages to summarize."
            
            # Extract common themes
            all_text = " ".join([msg.message_body.lower() for msg in client_messages])
            
            themes = []
            if any(word in all_text for word in ['dying', 'death', 'hospice', 'terminal']):
                themes.append("end-of-life care")
            if any(word in all_text for word in ['family', 'spouse', 'children']):
                themes.append("family support")
            if any(word in all_text for word in ['scared', 'afraid', 'anxious', 'worried']):
                themes.append("anxiety/fear")
            if any(word in all_text for word in ['pain', 'medical', 'doctor']):
                themes.append("medical concerns")
            if any(word in all_text for word in ['grief', 'sad', 'loss']):
                themes.append("grief support")
            
            summary_parts = [f"Conversation with {len(client_messages)} client messages."]
            
            if themes:
                summary_parts.append(f"Main themes: {', '.join(themes[:3])}.")
            
            # Check for escalation indicators
            if any(msg.contains_urgent_keywords for msg in messages):
                summary_parts.append("Contains urgent keywords requiring attention.")
            
            return " ".join(summary_parts)
            
        except Exception as e:
            logging.error(f"Error generating conversation summary: {str(e)}")
            return f"Summary generation failed: {str(e)}"

# Global instance - no API keys required
doula_ai = SimpleDoulaAI()