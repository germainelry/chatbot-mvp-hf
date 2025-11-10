"""
Seed database with sample knowledge base articles and demo conversations.
Run this after initializing the database.
"""
from app.database import SessionLocal, init_db
from app.models import KnowledgeBase, Conversation, Message, ConversationStatus, MessageType
from datetime import datetime, timedelta

def seed_knowledge_base(db):
    """Seed knowledge base with sample articles."""
    articles = [
        {
            "title": "Return & Refund Policy",
            "content": """Our return policy allows you to return items within 30 days of purchase for a full refund. Items must be in original condition with tags attached. To initiate a return:
1. Log into your account and go to Order History
2. Select the order and click 'Request Return'
3. Print the prepaid return label
4. Ship the item back within 5 business days

Refunds are processed within 5-7 business days after we receive the return. The refund will be credited to your original payment method. If you paid with a gift card, the refund will be issued as store credit.""",
            "category": "Returns",
            "tags": "return,refund,exchange,policy,30 days"
        },
        {
            "title": "Shipping Information",
            "content": """We offer multiple shipping options:

Standard Shipping (3-5 business days): $5.99 or FREE on orders over $50
Express Shipping (2-3 business days): $12.99
Overnight Shipping (1 business day): $24.99

Orders placed before 2 PM EST ship the same day. You'll receive a tracking number via email once your order ships. Track your order anytime by logging into your account or clicking the tracking link in your shipping confirmation email.

We ship to all 50 US states and international locations. International shipping times vary by destination (typically 7-14 business days).""",
            "category": "Shipping",
            "tags": "shipping,delivery,tracking,express,standard,overnight,free shipping"
        },
        {
            "title": "Account Management & Password Reset",
            "content": """To reset your password:
1. Go to the login page and click 'Forgot Password'
2. Enter your email address
3. Check your email for a password reset link (valid for 24 hours)
4. Click the link and create a new password

Password requirements: At least 8 characters, including one uppercase letter, one number, and one special character.

To update your account information:
- Log into your account
- Click on 'Account Settings'
- Update your email, shipping address, or payment methods
- Click 'Save Changes'

If you're having trouble accessing your account, contact our support team with your order number and we'll help you regain access.""",
            "category": "Account",
            "tags": "account,login,password,reset,email,settings,profile"
        },
        {
            "title": "Product Specifications & Warranty",
            "content": """All our products come with detailed specifications on the product page. Look for the 'Specifications' tab for:
- Dimensions and weight
- Materials and composition
- Care instructions
- Color options
- Compatibility information

Warranty Information:
All products include a 1-year manufacturer's warranty covering defects in materials and workmanship. This does not cover normal wear and tear, misuse, or accidental damage.

To file a warranty claim:
1. Contact our support team with your order number
2. Provide photos of the defect
3. We'll review and either replace or repair the item

Extended warranty options are available at checkout for select items.""",
            "category": "Products",
            "tags": "product,specifications,specs,warranty,guarantee,quality,details"
        }
    ]
    
    for article_data in articles:
        article = KnowledgeBase(**article_data)
        db.add(article)
    
    db.commit()
    print(f"✅ Seeded {len(articles)} knowledge base articles")


def seed_sample_conversations(db):
    """Seed sample conversations for demo purposes."""
    # Sample conversation 1 - Resolved
    conv1 = Conversation(
        customer_id="customer_001",
        status=ConversationStatus.RESOLVED,
        created_at=datetime.utcnow() - timedelta(hours=2),
        resolved_at=datetime.utcnow() - timedelta(hours=1)
    )
    db.add(conv1)
    db.flush()
    
    messages1 = [
        Message(
            conversation_id=conv1.id,
            content="Hi, I'd like to know about your return policy",
            message_type=MessageType.CUSTOMER,
            created_at=datetime.utcnow() - timedelta(hours=2)
        ),
        Message(
            conversation_id=conv1.id,
            content="Our return policy allows returns within 30 days of purchase for a full refund. Items must be in original condition. Would you like help initiating a return?",
            message_type=MessageType.FINAL,
            confidence_score=0.87,
            created_at=datetime.utcnow() - timedelta(hours=2, minutes=-5)
        ),
        Message(
            conversation_id=conv1.id,
            content="Yes, I need to return an order I placed last week",
            message_type=MessageType.CUSTOMER,
            created_at=datetime.utcnow() - timedelta(hours=1, minutes=50)
        ),
        Message(
            conversation_id=conv1.id,
            content="I can help with that! Please log into your account, go to Order History, and select 'Request Return' on the order. You'll get a prepaid return label. Is there anything else you need help with?",
            message_type=MessageType.FINAL,
            confidence_score=0.82,
            created_at=datetime.utcnow() - timedelta(hours=1, minutes=45)
        )
    ]
    
    for msg in messages1:
        db.add(msg)
    
    # Sample conversation 2 - Active (needs attention)
    conv2 = Conversation(
        customer_id="customer_002",
        status=ConversationStatus.ACTIVE,
        created_at=datetime.utcnow() - timedelta(minutes=30)
    )
    db.add(conv2)
    db.flush()
    
    messages2 = [
        Message(
            conversation_id=conv2.id,
            content="My order hasn't arrived yet and it's been over a week. Order #12345",
            message_type=MessageType.CUSTOMER,
            created_at=datetime.utcnow() - timedelta(minutes=30)
        ),
        Message(
            conversation_id=conv2.id,
            content="I can help you track your order. Could you please provide your order number so I can check the shipping status?",
            message_type=MessageType.AI_DRAFT,
            confidence_score=0.55,
            created_at=datetime.utcnow() - timedelta(minutes=29)
        )
    ]
    
    for msg in messages2:
        db.add(msg)
    
    # Sample conversation 3 - Escalated
    conv3 = Conversation(
        customer_id="customer_003",
        status=ConversationStatus.ESCALATED,
        created_at=datetime.utcnow() - timedelta(hours=5)
    )
    db.add(conv3)
    db.flush()
    
    messages3 = [
        Message(
            conversation_id=conv3.id,
            content="I received a damaged product and need a replacement immediately",
            message_type=MessageType.CUSTOMER,
            created_at=datetime.utcnow() - timedelta(hours=5)
        ),
        Message(
            conversation_id=conv3.id,
            content="I understand your concern about the damaged product. Let me escalate this to a specialist who can process an immediate replacement for you.",
            message_type=MessageType.AGENT_ONLY,
            confidence_score=None,
            created_at=datetime.utcnow() - timedelta(hours=5, minutes=-10)
        )
    ]
    
    for msg in messages3:
        db.add(msg)
    
    db.commit()
    print(f"✅ Seeded 3 sample conversations with messages")


def main():
    """Run all seed functions."""
    print("🌱 Starting database seeding...")
    
    # Initialize database
    init_db()
    print("✅ Database tables created")
    
    # Create session
    db = SessionLocal()
    
    try:
        # Check if already seeded
        existing_articles = db.query(KnowledgeBase).count()
        if existing_articles > 0:
            print("⚠️  Database already contains data. Skipping seed.")
            return
        
        # Seed data
        seed_knowledge_base(db)
        seed_sample_conversations(db)
        
        print("✅ Database seeding completed successfully!")
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()

