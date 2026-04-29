"""Contact management for Helios mobile app."""

import json
from pathlib import Path
from typing import Optional

try:
    from fuzzywuzzy import fuzz
    from fuzzywuzzy import process
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False
    print("Warning: fuzzywuzzy not available, using simple matching")


class ContactManager:
    """Manage contacts with fuzzy matching."""

    def __init__(self):
        self.contacts_file = Path(__file__).parent / ".helios_contacts"
        self._contacts: list[dict] = []
        self._load()

    def _load(self):
        """Load contacts from file."""
        if self.contacts_file.exists():
            try:
                data = json.loads(self.contacts_file.read_text())
                self._contacts = data.get("contacts", [])
            except Exception as e:
                print(f"Error loading contacts: {e}")
                self._contacts = []

    def _save(self):
        """Save contacts to file."""
        try:
            self.contacts_file.write_text(json.dumps({"contacts": self._contacts}))
        except Exception as e:
            print(f"Error saving contacts: {e}")

    def add_contact(self, name: str, phone: Optional[str] = None,
                    email: Optional[str] = None, aliases: Optional[list] = None):
        """Add a new contact."""
        contact = {
            "name": name,
            "phone": phone,
            "email": email,
            "aliases": aliases or [],
        }
        # Check if contact already exists
        existing = self.get_contact_by_name(name)
        if existing:
            # Update existing
            idx = self._contacts.index(existing)
            self._contacts[idx] = contact
        else:
            self._contacts.append(contact)
        self._save()

    def remove_contact(self, name: str):
        """Remove a contact by name."""
        self._contacts = [c for c in self._contacts if c["name"] != name]
        self._save()

    def get_contact_by_name(self, name: str) -> Optional[dict]:
        """Get contact by exact name match."""
        for contact in self._contacts:
            if contact["name"].lower() == name.lower():
                return contact
            # Check aliases
            for alias in contact.get("aliases", []):
                if alias.lower() == name.lower():
                    return contact
        return None

    def find_contact(self, query: str, threshold: int = 60) -> Optional[dict]:
        """Find contact using fuzzy matching.

        Args:
            query: Search query (e.g., "mum", "boss")
            threshold: Minimum match score (0-100)

        Returns:
            Best matching contact or None
        """
        if not self._contacts:
            return None

        if FUZZY_AVAILABLE:
            # Build search list with names and aliases
            search_list = []
            for contact in self._contacts:
                search_list.append(contact["name"])
                search_list.extend(contact.get("aliases", []))

            # Find best match
            match, score = process.extractOne(query, search_list)
            if score >= threshold:
                # Find the contact that has this match
                for contact in self._contacts:
                    if contact["name"] == match or match in contact.get("aliases", []):
                        return contact
            return None
        else:
            # Simple matching without fuzzywuzzy
            query_lower = query.lower()
            for contact in self._contacts:
                if query_lower in contact["name"].lower():
                    return contact
                for alias in contact.get("aliases", []):
                    if query_lower in alias.lower():
                        return contact
            return None

    def get_all_contacts(self) -> list[dict]:
        """Get all contacts."""
        return self._contacts.copy()

    def resolve_contact(self, name: str) -> dict:
        """Resolve contact name to full contact info.

        Returns contact dict with 'matched_name' indicating the matched name.
        If not found, returns a dict with name as-is and empty phone/email.
        """
        contact = self.find_contact(name)
        if contact:
            return {
                "name": contact["name"],
                "phone": contact.get("phone", ""),
                "email": contact.get("email", ""),
                "matched": True,
            }
        # Return as-is if not found
        return {
            "name": name,
            "phone": "",
            "email": "",
            "matched": False,
        }

    def import_android_contacts(self):
        """Import contacts from Android device."""
        try:
            from jnius import autoclass, cast
            Context = autoclass('android.content.Context')
            ContentResolver = autoclass('android.content.ContentResolver')
            ContactsContract = autoclass('android.provider.ContactsContract')

            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity = PythonActivity.mActivity
            content_resolver = activity.getContentResolver()

            # Query contacts
            cursor = content_resolver.query(
                ContactsContract.Contacts.CONTENT_URI,
                None, None, None, None
            )

            imported = 0
            while cursor.moveToNext():
                name = cursor.getString(
                    cursor.getColumnIndex(ContactsContract.Contacts.DISPLAY_NAME)
                )
                if name:
                    self.add_contact(name, phone="")
                    imported += 1

            cursor.close()
            return imported
        except Exception as e:
            print(f"Error importing contacts: {e}")
            return 0


# Global contact manager instance
contact_manager = ContactManager()
