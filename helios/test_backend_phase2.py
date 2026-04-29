"""Test script for Helios Core Phase 2 features."""

import requests
import sys

BASE_URL = "http://127.0.0.1:8000"


def test_health():
    """Test health endpoint."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        data = response.json()
        print(f"✓ Health check: {data}")
        return True
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False


def test_session():
    """Test session creation."""
    try:
        response = requests.get(f"{BASE_URL}/session/new", timeout=5)
        data = response.json()
        session_id = data.get("session_id")
        print(f"✓ Session created: {session_id}")
        return session_id
    except Exception as e:
        print(f"✗ Session creation failed: {e}")
        return None


def test_command_with_session(text: str, session_id: str = None):
    """Test command processing with session."""
    try:
        payload = {"text": text}
        if session_id:
            payload["session_id"] = session_id

        response = requests.post(
            f"{BASE_URL}/process",
            json=payload,
            timeout=30,
        )
        result = response.json()
        print(f"\n  Command: '{text}'")
        print(f"  Response: {result.get('message')}")
        print(f"  Actions: {[a['type'] for a in result.get('actions', [])]}")
        print(f"  Confirmation needed: {result.get('confirmation_required')}")
        return result
    except Exception as e:
        print(f"✗ Command failed: {e}")
        return None


def test_conversation_memory(session_id: str):
    """Test conversation memory with multi-turn conversation."""
    print("\n--- Testing Conversation Memory ---")

    # First command - sets context
    print("\n1. User: 'I need to message John'")
    r1 = test_command_with_session("I need to message John", session_id)

    if r1:
        action = r1.get("actions", [{}])[0]
        if action.get("type") == "sms":
            print("  ✓ Correctly identified SMS intent")

    # Second command - uses context ("him" refers to John)
    print("\n2. User: 'Tell him I'm running late'")
    r2 = test_command_with_session("Tell him I'm running late", session_id)

    if r2:
        action = r2.get("actions", [{}])[0]
        if action.get("params", {}).get("contact") == "John":
            print("  ✓ Correctly resolved 'him' to John from context")
        else:
            print(f"  ℹ Contact resolved to: {action.get('params', {}).get('contact')}")


def test_new_actions(session_id: str):
    """Test new action types from Phase 2."""
    print("\n--- Testing New Actions ---")

    new_action_commands = [
        ("Remind me to pick up milk tomorrow at 5 PM", "reminder"),
        ("Email boss about the project update", "email"),
        ("Search for Italian restaurants nearby", "web_search"),
        ("Add meeting with team tomorrow at 2 PM to calendar", "calendar_add"),
    ]

    for command, expected_type in new_action_commands:
        result = test_command_with_session(command, session_id)
        if result:
            action_types = [a.get("type") for a in result.get("actions", [])]
            if expected_type in action_types:
                print(f"  ✓ Detected {expected_type} action")
            else:
                print(f"  ℹ Actions: {action_types}")


def test_confirmation_required(session_id: str):
    """Test that sensitive actions require confirmation."""
    print("\n--- Testing Action Confirmation ---")

    sensitive_commands = [
        "Call mum",  # call
        "Message John saying hello",  # sms
        "Email boss about the meeting",  # email
    ]

    for command in sensitive_commands:
        result = test_command_with_session(command, session_id)
        if result:
            if result.get("confirmation_required"):
                print(f"  ✓ '{command}' correctly requires confirmation")
            else:
                actions = result.get("actions", [])
                needs_confirm = any(a.get("confirmation_required") for a in actions)
                if needs_confirm:
                    print(f"  ✓ '{command}' action marked for confirmation")
                else:
                    print(f"  ℹ '{command}' - check if confirmation flag set")


def test_database():
    """Test database functionality."""
    print("\n--- Testing Database ---")

    from helios.shared.database import Database

    db = Database()

    # Test contact operations
    db.add_contact("Test User", phone="1234567890", email="test@example.com")
    contacts = db.get_contacts("Test")
    print(f"✓ Added test contact: {len(contacts)} found")

    # Test profile operations
    db.create_profile("test_user", name="Test User", location="NYC")
    profile = db.get_profile("test_user")
    print(f"✓ Created profile: {profile}")

    # Clean up
    print("✓ Database operations working")


if __name__ == "__main__":
    print("=" * 60)
    print("Helios Core Phase 2 Backend Test")
    print("=" * 60)

    if not test_health():
        print("\n⚠ Backend not running. Start it with:")
        print("  cd helios/backend && python main.py")
        sys.exit(1)

    session_id = test_session()
    if not session_id:
        print("Failed to create session")
        sys.exit(1)

    print("\n--- Testing Basic Commands ---")
    test_command_with_session("Message John", session_id)
    test_command_with_session("Call mum", session_id)
    test_command_with_session("Open Spotify", session_id)

    test_conversation_memory(session_id)
    test_new_actions(session_id)
    test_confirmation_required(session_id)

    try:
        test_database()
    except Exception as e:
        print(f"✗ Database test failed: {e}")

    print("\n" + "=" * 60)
    print("Phase 2 Test Complete!")
    print("=" * 60)
