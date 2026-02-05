# assistant/memory/contacts.py
class ContactBook:
    def __init__(self, memory):
        self.memory = memory

    def get_contact(self, name: str):
        contacts = self.memory.get("contacts", {})
        return contacts.get(name.lower())

    def add_contact(self, name: str, identifier: str):
        contacts = self.memory.get("contacts", {})
        contacts[name.lower()] = identifier
        self.memory.set("contacts", contacts)
