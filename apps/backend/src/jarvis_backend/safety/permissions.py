# assistant/safety/permissions.py
class PermissionManager:
    def request(self, tool_name: str, details: str) -> bool:
        print(f"\n🔐 Permission required for tool: {tool_name}")
        print(f"Details: {details}")
        answer = input("Allow? (yes/no): ").strip().lower()
        return answer == "yes"
