# assistant/voice/conversation_manager.py
import queue

class ConversationManager:

    def __init__(self):
        self.current_intent = None
        self.pending_intents = queue.Queue()
        self.is_processing = False

    def interrupt(self, new_command):
        """
        Called when user speaks during thinking/speaking
        """

        if self.is_related(new_command):
            return ("merge", new_command)
        else:
            self.pending_intents.put(new_command)
            return ("queue", new_command)

    def next_pending(self):
        if not self.pending_intents.empty():
            return self.pending_intents.get()
        return None

    def is_related(self, new_command):
        continuation_words = [
            "actually",
            "instead",
            "change",
            "modify",
            "make it",
            "no",
            "wait"
        ]

        return any(w in new_command.lower() for w in continuation_words)
