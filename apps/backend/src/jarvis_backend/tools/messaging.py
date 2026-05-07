from jarvis_backend.tools.base import BaseTool


class MessagingTool(BaseTool):
    name = "message"
    description = "Send a message to a contact"
    requires_permission = True

    def run(self, **kwargs) -> str:
        contact = kwargs.get("contact", "")
        message = kwargs.get("message", "")

        if not contact or not message:
            return "Error: Both 'contact' and 'message' parameters are required."

        return f'(Mock) Message sent to {contact}: "{message}"'
