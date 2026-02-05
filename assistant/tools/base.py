# assistant/tools/base.py
from abc import ABC, abstractmethod

class BaseTool(ABC):
    name: str
    description: str
    requires_permission: bool = True

    @abstractmethod
    def run(self, **kwargs) -> str:
        pass
