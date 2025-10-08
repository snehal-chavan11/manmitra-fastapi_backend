import google.generativeai as genai
from typing import List, Dict, Any, Optional
import json
import asyncio
import time
import hashlib
from datetime import datetime, timedelta
from app.core.config import settings
from app.core.security import safety_service

class GeminiService:
    """Service for interacting with Google Gemini AI with rate limiting and caching"""
    
    def __init__(self):
        self.model = None
        self._initialize_model()
        
        # Rate limiting (Gemini free tier: 15 RPM)
        self.requests_per_minute = 10  # Conservative limit
        self.max_tokens_per_day = 50000  # Conservative daily limit
        self.request_timestamps = []
        self.daily_token_count = 0
        self.last_reset_date = datetime.now().date()
        
        # Caching for similar requests
        self.response_cache = {}
        self.cache_ttl = 3600  # 1 hour cache TTL
        
        # Backoff strategy
        self.backoff_until = None
        self.consecutive_failures = 0
    
    def _initialize_model(self):
        """Initialize the Gemini model"""
        try:
            if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY.strip() == "":
                print("⚠️  No Gemini API key found - running in fallback mode")
                self.model = None
                return
                
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
            print("✅ Gemini model initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize Gemini model: {e} - running in fallback mode")
            self.model = None
    
    def _check_rate_limit(self) -> bool:
        """Check if we can make an API request based on rate limits"""
        now = datetime.now()
        
        # Reset daily counter if new day
        if now.date() > self.last_reset_date:
            self.daily_token_count = 0
            self.last_reset_date = now.date()
            print(f"🔄 Daily token counter reset")
        
        # Check if we're in backoff period
        if self.backoff_until and now < self.backoff_until:
            remaining = (self.backoff_until - now).seconds
            print(f"⏳ In backoff period, {remaining} seconds remaining")
            return False
        
        # Clean old timestamps (keep only last minute)
        cutoff = now - timedelta(minutes=1)
        self.request_timestamps = [ts for ts in self.request_timestamps if ts > cutoff]
        
        # Check RPM limit
        if len(self.request_timestamps) >= self.requests_per_minute:
            print(f"⚠️ Rate limit exceeded: {len(self.request_timestamps)}/{self.requests_per_minute} RPM")
            return False
        
        return True
    
    def _get_cache_key(self, prompt: str, temperature: float) -> str:
        """Generate cache key for the request"""
        # Create hash of prompt + temperature for caching
        content = f"{prompt}_{temperature}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        """Get cached response if available and not expired"""
        if cache_key not in self.response_cache:
            return None
        
        cached_data = self.response_cache[cache_key]
        if datetime.now() - cached_data['timestamp'] > timedelta(seconds=self.cache_ttl):
            # Cache expired
            del self.response_cache[cache_key]
            return None
        
        print(f"💾 Using cached response for request")
        return cached_data['response']
    
    def _cache_response(self, cache_key: str, response: str):
        """Cache the response"""
        self.response_cache[cache_key] = {
            'response': response,
            'timestamp': datetime.now()
        }
        
        # Limit cache size (keep last 100 entries)
        if len(self.response_cache) > 100:
            oldest_key = min(self.response_cache.keys(), 
                           key=lambda k: self.response_cache[k]['timestamp'])
            del self.response_cache[oldest_key]
    
    def _handle_rate_limit_error(self, error: Exception):
        """Handle rate limit errors with intelligent backoff"""
        self.consecutive_failures += 1
        
        # Extract retry delay from error message if available
        error_str = str(error)
        if "retry_delay" in error_str or "30" in error_str:
            backoff_seconds = 35  # Add a bit extra to the suggested 30s
        else:
            # Exponential backoff: 2^failures * 30 seconds, max 10 minutes
            backoff_seconds = min(2 ** self.consecutive_failures * 30, 600)
        
        self.backoff_until = datetime.now() + timedelta(seconds=backoff_seconds)
        
        print(f"🚫 Rate limit hit. Backing off for {backoff_seconds} seconds")
        print(f"📊 API Usage Stats: RPM: {len(self.request_timestamps)}, Daily tokens: {self.daily_token_count}")
    
    def get_api_status(self) -> Dict[str, Any]:
        """Get current API status and usage statistics"""
        now = datetime.now()
        
        # Clean old timestamps
        cutoff = now - timedelta(minutes=1)
        self.request_timestamps = [ts for ts in self.request_timestamps if ts > cutoff]
        
        return {
            "api_key_configured": self.model is not None,
            "requests_this_minute": len(self.request_timestamps),
            "requests_per_minute_limit": self.requests_per_minute,
            "tokens_used_today": self.daily_token_count,
            "daily_token_limit": self.max_tokens_per_day,
            "in_backoff": self.backoff_until is not None and now < self.backoff_until,
            "backoff_until": self.backoff_until.isoformat() if self.backoff_until else None,
            "consecutive_failures": self.consecutive_failures,
            "cache_size": len(self.response_cache),
            "quota_exhausted": self.daily_token_count >= self.max_tokens_per_day
        }
    
    def generate_response(self, prompt: str, temperature: float = 0.7) -> str:
        """Generate response from Gemini model with rate limiting and caching"""
        try:
            if self.model is None:
                return self._generate_fallback_response(prompt)
            
            # Check cache first
            cache_key = self._get_cache_key(prompt, temperature)
            cached_response = self._get_cached_response(cache_key)
            if cached_response:
                return cached_response
            
            # Check rate limits
            if not self._check_rate_limit():
                print(f"⚠️ Rate limit exceeded, using fallback response")
                return self._generate_fallback_response(prompt)
            
            # Record request timestamp
            self.request_timestamps.append(datetime.now())
            
            # Estimate tokens (rough estimate: 1 token ≈ 4 characters)
            estimated_tokens = len(prompt) // 4 + 150  # Add output tokens estimate
            
            # Check daily token limit
            if self.daily_token_count + estimated_tokens >= self.max_tokens_per_day:
                print(f"⚠️ Daily token limit would be exceeded, using fallback")
                return self._generate_fallback_response(prompt)
            
            # Generate response - FIXED: No system role, just direct prompt
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=400,  # Reduced to save quota
                    top_p=0.8,
                    top_k=40
                )
            )
            
            # Update token count
            self.daily_token_count += estimated_tokens
            self.consecutive_failures = 0  # Reset on success
            
            # Cache the response
            response_text = response.text
            self._cache_response(cache_key, response_text)
            
            print(f"✅ Gemini API success. Tokens used: ~{estimated_tokens}, Daily total: {self.daily_token_count}")
            
            return response_text
            
        except Exception as e:
            error_str = str(e)
            print(f"Error generating response: {error_str}")
            
            # Handle rate limit errors specifically
            if "quota" in error_str.lower() or "429" in error_str or "rate" in error_str.lower():
                self._handle_rate_limit_error(e)
            
            return self._generate_fallback_response(prompt)
    
    def _generate_fallback_response(self, prompt: str) -> str:
        """Generate an intelligent fallback response when AI is not available"""
        import random
        
        prompt_lower = prompt.lower()
        
        # Multi-language anxiety responses (first-aid with coping strategies)
        if any(word in prompt_lower for word in ['anxious', 'worried', 'panic', 'overwhelmed', 'stressed', 'चिंता', 'परेशान', 'تناؤ', 'tension']):
            responses = [
                "Yaar, I can tell you're feeling anxious right now. Let's try this first-aid technique: Take 4 deep breaths - in for 4, hold for 4, out for 4. What's causing this stress, bro?",
                "Bhai, anxiety feels overwhelming na? Try the 5-4-3-2-1 technique: Name 5 things you see, 4 you can touch, 3 you hear, 2 you smell, 1 you taste. Kya specific thing is worrying you?",
                "Dude, that anxiety is real but manageable. Quick tip: Put your hand on your chest, feel your heartbeat, breathe with it. Now tell me what's the main stressor?",
                "Hey yaar, anxiety attack? Try cold water on your wrists or drink some water slowly. Main hoon na - what's weighing heavy on your mind right now?"
            ]
            return random.choice(responses)
        
        # Multi-language sadness responses (first-aid with coping strategies)
        elif any(word in prompt_lower for word in ['sad', 'depressed', 'down', 'hopeless', 'empty', 'उदास', 'दुखी', 'غمگین', 'udaas']):
            responses = [
                "Bro, sounds like you're going through a tough time. Quick first-aid: Try to get some sunlight or bright light, even for 10 minutes. Your feelings are valid - what's been happening?",
                "Yaar, I can hear you're struggling. First-aid tip: Do one small thing you normally enjoy - chai, music, calling a friend. Kab se feeling this way?",
                "Bhai, those heavy feelings are real. Try this: Write down 3 small things you're grateful for today. Main yahan hoon - what's been the hardest part?",
                "Dude, when feeling low, movement helps - even 5 minutes walking. Your feelings matter, no judgment here. Kya specifically going on?"
            ]
            return random.choice(responses)
        
        # Academic stress (first-aid with study coping strategies)
        elif any(word in prompt_lower for word in ['study', 'exam', 'academic', 'pressure', 'grades', 'पढ़ाई', 'امتحان', 'padhai', 'imtihaan']):
            responses = [
                "Yaar, academic pressure is real. First-aid tip: Break your study into 25-min chunks with 5-min breaks (Pomodoro). Your worth isn't your grades, bro. Which subject is stressing you most?",
                "Bhai, exam stress is tough! Try this: Study for 45 mins, then do something fun for 15 mins. You're doing your best - what's the biggest challenge abhi?",
                "Dude, study pressure getting to you? Quick tip: Make a simple today-only to-do list with just 3 tasks. Sab students feel this - what would help you feel more prepared?",
                "Bro, studies overwhelming you? Try the 2-minute rule: If it takes less than 2 mins, do it now. You're more than your marks - kya specifically bothering you?"
            ]
            return random.choice(responses)
        
        # General supportive responses (bro style with multilingual)
        else:
            responses = [
                "Thanks for sharing that with me, yaar. Your feelings are completely valid. What's been on your mind lately?",
                "Bro, I can hear this is important to you. What would be most helpful to talk about right now?",
                "Takes courage to reach out, dude. I'm glad you're here. Kaisa feeling today?",
                "Yaar, that sounds like a lot to handle. What's been the most challenging part for you?",
                "I'm here to listen and support you, bhai. What's weighing on your dil right now?",
                "That sounds tough to deal with, bro. You don't have to face this alone. Kya chal raha hai?",
                "Hey yaar, main sun raha hoon. Whatever it is, we can talk through it. What's going on?"
            ]
            return random.choice(responses)
    
    async def generate_response_async(self, prompt: str, temperature: float = 0.7) -> str:
        """Async version of generate_response"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.generate_response, prompt, temperature)

class BestieService:
    """Service for Bestie chatbot functionality"""
    
    def __init__(self):
        self.gemini_service = GeminiService()
    
    async def process_message(self, message: str, history: List[Dict], user_id: Optional[str] = None, topic: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a user message and generate appropriate response
        """
        try:
            # Validate message
            validation = safety_service.validate_message(message)
            if not validation["is_valid"]:
                return {
                    "type": "error",
                    "message": f"Invalid message: {validation['reason']}",
                    "metadata": {"validation_error": True}
                }
            
            message = validation["sanitized_text"]
            
            # Check for crisis indicators
            crisis_detection = safety_service.detect_crisis(message)
            if crisis_detection["is_crisis"]:
                return await self._handle_crisis_response(crisis_detection)
            
            # Generate response using simplified approach
            response = await self._generate_simple_response(message, history, topic)
            
            return {
                "response": response,
                "agent": "listener",
                "crisis_detected": False,
                "crisis_level": None,
                "type": "chat",
                "metadata": {
                    "topic": topic,
                    "user_id": user_id,
                    "is_crisis": False
                }
            }
            
        except Exception as e:
            print(f"Error processing message: {e}")
            return {
                "response": "Hey yaar, I'm your first-aid mental health bro. Sometimes my connection acts up, but I'm still here for you. Take a deep breath with me - what's going on today?",
                "agent": "listener",
                "crisis_detected": False,
                "type": "chat",
                "metadata": {"error": str(e)}
            }
    
    async def _generate_simple_response(self, message: str, history: List[Dict], topic: Optional[str]) -> str:
        """Generate response using simplified approach that works with Gemini"""
        
        # Create a simple, direct prompt without system roles
        context_lines = []
        
        # Add topic context if available
        if topic:
            context_lines.append(f"Topic: {topic}")
        
        # Add recent history (last 3 messages)
        if history:
            context_lines.append("Recent conversation:")
            for msg in history[-3:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                context_lines.append(f"{role}: {content}")
        
        # Build the complete prompt
        prompt_parts = [
            "You are Bestie, an AI-guided first-aid mental health support companion for students.",
            "Role: Provide immediate emotional first-aid, practical coping strategies, and refer to professionals when needed.",
            "Personality: Supportive bro who's got your back - understanding, real, and helpful with practical solutions.",
            "Language: Mix English, Hindi, Hinglish, Urdu, Roman Urdu naturally. Use bro terms like 'bhai', 'yaar', 'dude', 'bro'.",
            "First-Aid Focus: Offer 1-2 practical coping strategies, validate feelings, provide immediate support.",
            "Boundaries: You're first-aid support, not therapy. Refer to counselors for complex issues. Never diagnose."
        ]
        
        if context_lines:
            prompt_parts.append("\n" + "\n".join(context_lines))
        
        prompt_parts.append(f"\nUser: {message}")
        prompt_parts.append("\nBestie: ")
        
        full_prompt = "\n".join(prompt_parts)
        
        try:
            # Use the Gemini service to generate response
            response = await self.gemini_service.generate_response_async(full_prompt, temperature=0.7)
            
            # Clean up the response
            response = response.strip()
            
            # Remove any "Bestie:" prefix if the model added it
            if response.startswith("Bestie:"):
                response = response[7:].strip()
            
            return response
            
        except Exception as e:
            print(f"Error in simple response generation: {e}")
            return self.gemini_service._generate_fallback_response(message)
    
    async def _handle_crisis_response(self, crisis_detection: Dict[str, Any]) -> Dict[str, Any]:
        """Handle crisis detection response"""
        severity = crisis_detection["severity"]
        
        if severity == "high":
            response = """I'm really concerned about what you're telling me. It sounds like you're going through an incredibly difficult time right now. 

Your life has value, and there are people who care about you and want to help. Please reach out to a crisis helpline or emergency services immediately:

• KIRAN Mental Health Helpline: 1800-599-0019 (24/7)
• Emergency Services: 112
• Tele-MANAS: 104

You don't have to face this alone. There is help available, and things can get better."""
        elif severity == "medium":
            response = """I can hear that you're really struggling right now, and I'm worried about you. These feelings are valid, and it's important that you get support.

Please consider reaching out to:
• A trusted friend or family member
• A counselor or mental health professional
• KIRAN Helpline: 1800-599-0019

You deserve support and care. Please don't hesitate to reach out for help."""
        else:
            response = """I can sense that you're going through a tough time. It's okay to feel overwhelmed sometimes.

If you'd like to talk to someone who can provide more support, I'd encourage you to consider speaking with a counselor or reaching out to the KIRAN helpline at 1800-599-0019.

You're not alone in this, and there are people who want to help."""
        
        return {
            "response": response,
            "agent": "crisis",
            "crisis_detected": True,
            "crisis_level": severity,
            "type": "crisis",
            "metadata": {
                "severity": severity,
                "matched_patterns": crisis_detection["matched_patterns"],
                "requires_immediate_attention": severity in ["high", "medium"]
            }
        }

class ModerationService:
    """Service for content moderation using AI"""
    
    def __init__(self):
        self.gemini_service = GeminiService()
    
    async def moderate_post(self, text: str) -> Dict[str, Any]:
        """Moderate forum post content"""
        try:
            # Simplified moderation prompt
            prompt = f"""Analyze this text for a student mental health forum:

"{text}"

Is this appropriate? Consider: toxicity, self-harm promotion, harassment.
Respond ONLY with JSON: {{"decision": "allow" or "block", "confidence": 0.0-1.0, "reason": "brief explanation"}}"""
            
            response = await self.gemini_service.generate_response_async(prompt, temperature=0.2)
            
            try:
                moderation_result = json.loads(response.strip())
                return {
                    "decision": moderation_result.get("decision", "allow"),
                    "confidence": moderation_result.get("confidence", 0.5),
                    "reason": moderation_result.get("reason", "AI moderation analysis"),
                    "method": "gemini"
                }
            except json.JSONDecodeError:
                return self._fallback_moderation(text)
            
        except Exception as e:
            print(f"Error in AI moderation: {e}")
            return self._fallback_moderation(text)
    
    def _fallback_moderation(self, text: str) -> Dict[str, Any]:
        """Fallback moderation using rule-based approach"""
        toxic_keywords = [
            "hate", "kill", "die", "abuse", "fuck", "shit", "bitch", "asshole",
            "suicide", "harm", "violence", "threat", "bomb", "attack"
        ]
        
        if any(kw in text.lower() for kw in toxic_keywords):
            return {
                "decision": "block",
                "confidence": 0.8,
                "reason": "Contains potentially harmful or inappropriate language",
                "method": "rule_based"
            }
        else:
            return {
                "decision": "allow",
                "confidence": 0.8,
                "reason": "No issues detected",
                "method": "rule_based"
            }

# Create service instances
bestie_service = BestieService()
moderation_service = ModerationService()
