# assistant/memory/user_profile.py
class UserProfile:
    def __init__(self, memory):
        self.memory = memory

    def exists(self) -> bool:
        return self.memory.get("user_profile") is not None

    def get(self) -> dict:
        return self.memory.get("user_profile", {})

    def set(self, profile: dict):
        self.memory.set("user_profile", profile)

    def update(self, key: str, value):
        profile = self.get()
        profile[key] = value
        self.set(profile)
