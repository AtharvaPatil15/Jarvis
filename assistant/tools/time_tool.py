from datetime import datetime
from assistant.tools.base_tool import BaseTool

class TimeTool(BaseTool):
    name = "time"
    description = "Get the current system time"

    def execute(self, input_text: str) -> str:
        now = datetime.now().strftime("%H:%M:%S")
        return f"The current time is {now}"
