"""
Router Agent - Classifies user intent and routes to appropriate agent.
Uses embedding similarity for few-shot intent classification.
"""
from typing import Dict, Optional, List
from app.services.rag_service import generate_embedding, cosine_similarity, EMBEDDING_AVAILABLE

# Intent categories
INTENT_CATEGORIES = [
    "faq",
    "order_inquiry",
    "technical_support",
    "complaint",
    "general"
]

# Intent examples for few-shot classification (expanded for better coverage)
INTENT_EXAMPLES = {
    "faq": [
        # Return/Refund policies
        "What is your return policy?",
        "How do I return an item?",
        "What is your refund policy?",
        "Do you offer exchanges?",
        "How long do I have to return something?",
        # Shipping questions
        "What are your shipping options?",
        "How much does shipping cost?",
        "Do you ship internationally?",
        "What are the delivery times?",
        "Is there free shipping?",
        # Account questions
        "How do I reset my password?",
        "How do I create an account?",
        "How do I update my email address?",
        "Can I change my password?",
        "How do I close my account?",
        # Payment questions
        "What payment methods do you accept?",
        "Do you accept PayPal?",
        "Is it safe to use my credit card?",
        "Can I pay with gift cards?",
        # Product questions
        "What are your business hours?",
        "Where are you located?",
        "Do you have a warranty?",
        "What is your price match policy?",
        "Do you offer gift wrapping?",
    ],
    "order_inquiry": [
        # Order status
        "Where is my order?",
        "When will my order arrive?",
        "What's the status of order #12345?",
        "Has my order shipped yet?",
        "Why hasn't my order arrived?",
        "Track my order",
        "Check order status",
        # Order modifications
        "I need to cancel my order",
        "Can I modify my order?",
        "Can I change my shipping address?",
        "Can I add items to my order?",
        "Can I remove items from my order?",
        "I want to change my order",
        # Order issues
        "I never received my order",
        "My tracking number isn't working",
        "Part of my order is missing",
        "Wrong item in my order",
        "Duplicate order placed",
    ],
    "technical_support": [
        # Website/app issues
        "The website is not working",
        "The app keeps crashing",
        "I can't load the page",
        "The site is slow",
        "Error message on website",
        "Page won't load",
        # Login/access issues
        "I can't log into my account",
        "Login not working",
        "Forgot my password",
        "Account locked",
        "Can't access my account",
        # Checkout/payment issues
        "I'm having trouble with checkout",
        "The payment failed",
        "Checkout isn't working",
        "Payment declined",
        "Can't complete purchase",
        "Error at checkout",
        "Credit card not accepted",
        # Other technical issues
        "Images not loading",
        "Can't download receipt",
        "Promo code not working",
        "Email confirmation not received",
    ],
    "complaint": [
        # Product complaints
        "I'm not happy with my purchase",
        "The product arrived damaged",
        "This product is defective",
        "Product doesn't match description",
        "Poor quality product",
        "Item broken on arrival",
        # Service complaints
        "The service was terrible",
        "I want to file a complaint",
        "This is unacceptable",
        "Very disappointed",
        "Horrible experience",
        "Terrible customer service",
        # Delivery complaints
        "Package arrived late",
        "Delivery person was rude",
        "Package left in rain",
        "Wrong item delivered",
        "Never received my package",
    ],
    "general": [
        # Greetings
        "Hello",
        "Hi there",
        "Hey",
        "Good morning",
        "Hi",
        # Help requests
        "Help me",
        "I need assistance",
        "Can you help?",
        "Need help",
        "I have a question",
        # Capability questions
        "What can you do?",
        "What can you help me with?",
        "How can you assist?",
        "What services do you offer?",
        # Thank you/goodbye
        "Thank you",
        "Thanks",
        "Goodbye",
        "Bye",
    ]
}


def classify_intent(user_message: str) -> Dict[str, any]:
    """
    Classify user intent using embedding similarity to intent examples.
    Returns intent category and confidence score.
    """
    if not EMBEDDING_AVAILABLE:
        # Fallback to keyword-based classification
        return classify_intent_keyword(user_message)
    
    # Generate embedding for user message
    user_embedding = generate_embedding(user_message.lower())
    if user_embedding is None:
        return classify_intent_keyword(user_message)
    
    # Calculate similarity to each intent category
    intent_scores = {}
    for intent, examples in INTENT_EXAMPLES.items():
        # Get average embedding for intent examples
        example_embeddings = []
        for example in examples:
            emb = generate_embedding(example.lower())
            if emb:
                example_embeddings.append(emb)

        if example_embeddings:
            # Calculate similarity to all examples
            similarities = [
                cosine_similarity(user_embedding, ex_emb)
                for ex_emb in example_embeddings
            ]
            # Use average of top 3 similarities for more robust scoring
            # This is less sensitive to outliers than max, and more discriminative than average
            top_similarities = sorted(similarities, reverse=True)[:3]
            intent_scores[intent] = sum(top_similarities) / len(top_similarities)
    
    if not intent_scores:
        return {
            "intent": "general",
            "confidence": 0.5
        }

    # Get intent with highest score
    sorted_intents = sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)
    best_intent, best_score = sorted_intents[0]

    # Calculate confidence with margin boost
    # If there's a clear winner (large margin), boost confidence
    if len(sorted_intents) > 1:
        second_best_score = sorted_intents[1][1]
        margin = best_score - second_best_score

        # Boost confidence if there's a clear margin (>0.1)
        # This helps simple, clear questions get higher confidence
        if margin > 0.15:
            confidence = min(best_score + 0.1, 1.0)  # Boost by 0.1, cap at 1.0
        elif margin > 0.08:
            confidence = min(best_score + 0.05, 1.0)  # Smaller boost
        else:
            confidence = best_score  # Ambiguous case, use raw score
    else:
        confidence = best_score

    return {
        "intent": best_intent,
        "confidence": float(confidence),
        "all_scores": intent_scores
    }


def classify_intent_keyword(user_message: str) -> Dict[str, any]:
    """
    Fallback keyword-based intent classification with improved patterns.
    """
    user_lower = user_message.lower()

    # Enhanced keyword patterns with weighted scoring
    keyword_patterns = {
        "order_inquiry": {
            "strong": ["order #", "tracking", "track order", "order status", "where is my order"],
            "medium": ["order", "shipment", "delivery", "package"],
            "weak": ["cancel", "modify", "change order"]
        },
        "technical_support": {
            "strong": ["not working", "error message", "can't log", "won't load", "keeps crashing"],
            "medium": ["error", "bug", "crash", "broken", "login issue"],
            "weak": ["help", "problem", "issue", "trouble"]
        },
        "complaint": {
            "strong": ["file a complaint", "very disappointed", "this is unacceptable", "terrible service"],
            "medium": ["complaint", "unhappy", "disappointed", "frustrated", "angry"],
            "weak": ["bad", "damaged", "wrong", "defective", "poor"]
        },
        "faq": {
            "strong": ["return policy", "refund policy", "shipping cost", "business hours"],
            "medium": ["policy", "how do i", "what is", "do you have", "can i"],
            "weak": ["return", "refund", "shipping", "warranty"]
        },
    }

    scores = {}
    for intent, patterns in keyword_patterns.items():
        score = 0
        # Strong keywords: 1.0 point each
        score += sum(1.0 for keyword in patterns["strong"] if keyword in user_lower)
        # Medium keywords: 0.5 points each
        score += sum(0.5 for keyword in patterns["medium"] if keyword in user_lower)
        # Weak keywords: 0.2 points each
        score += sum(0.2 for keyword in patterns["weak"] if keyword in user_lower)

        # Normalize by dividing by max possible score (all strong keywords)
        max_score = len(patterns["strong"]) * 1.0
        scores[intent] = min(score / max_score, 1.0) if max_score > 0 else 0

    # Check for greetings
    greetings = ["hello", "hi", "hey", "good morning", "good afternoon"]
    if any(greeting in user_lower for greeting in greetings) and len(user_lower.split()) <= 3:
        return {
            "intent": "general",
            "confidence": 0.7  # Higher confidence for clear greetings
        }

    if not scores or max(scores.values()) == 0:
        return {
            "intent": "general",
            "confidence": 0.5
        }

    best_intent = max(scores, key=scores.get)
    confidence = scores[best_intent]

    # Boost confidence if score is high (keyword-based is less reliable than embedding)
    if confidence > 0.6:
        confidence = min(confidence + 0.1, 0.85)  # Cap at 0.85 for keyword-based

    return {
        "intent": best_intent,
        "confidence": float(confidence)
    }


def should_escalate(intent: str, confidence: float, user_message: str) -> bool:
    """
    Determine if conversation should be escalated to human agent.
    Escalation triggers:
    - Low confidence (< 0.4)
    - Complaint intent (always escalate)
    - Explicit escalation request
    """
    # Explicit escalation request
    escalation_keywords = ["human", "agent", "representative", "speak to someone", "escalate"]
    if any(keyword in user_message.lower() for keyword in escalation_keywords):
        return True
    
    # Complaint intent always escalates
    if intent == "complaint":
        return True
    
    # Low confidence
    if confidence < 0.4:
        return True
    
    return False

