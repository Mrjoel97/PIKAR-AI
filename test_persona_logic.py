import os
import asyncio
from dotenv import load_dotenv
from app.services.user_onboarding_service import UserOnboardingService, UserPersona

load_dotenv()

def test_logic():
    service = UserOnboardingService()
    
    # Test Cases
    cases = [
        {"team_size": "solo", "role": "founder", "industry": "tech"},
        {"team_size": "Just Me (Solopreneur)", "role": "founder", "industry": "tech"}, # Potential frontend mismatch
        {"team_size": "startup", "role": "founder", "industry": "tech"},
        {"team_size": "1", "role": "founder", "industry": "tech"},
    ]
    
    print("\n--- Testing Persona Logic ---\n")
    for ctx in cases:
        persona = service._determine_persona(ctx)
        print(f"Input: {ctx['team_size']} -> Persona: {persona.value}")

if __name__ == "__main__":
    test_logic()
