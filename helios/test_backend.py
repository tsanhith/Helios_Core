"""Test script for backend API."""

import requests
import sys

BASE_URL = "http://127.0.0.1:8000"


def test_health():
    """Test health endpoint."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"✓ Health check: {response.json()}")
        return True
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False


def test_command(text: str):
    """Test command processing."""
    try:
        response = requests.post(
            f"{BASE_URL}/process",
            json={"text": text},
            timeout=30,
        )
        result = response.json()
        print(f"\nCommand: '{text}'")
        print(f"Response: {result['message']}")
        print(f"Actions: {[a['type'] for a in result['actions']]}")
        return True
    except Exception as e:
        print(f"✗ Command failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Helios Core Backend Test")
    print("=" * 50)

    if not test_health():
        print("\n⚠ Backend not running. Start it with:")
        print("  cd helios/backend && python main.py")
        sys.exit(1)

    print("\n--- Testing Commands ---")
    test_command("Message John")
    test_command("Call mum")
    test_command("Open Spotify")
    test_command("Send WhatsApp to Rahul")

    print("\n" + "=" * 50)
    print("Test complete!")
