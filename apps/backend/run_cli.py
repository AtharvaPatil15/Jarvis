from pathlib import Path
import sys


APP_DIR = Path(__file__).resolve().parent
SRC_DIR = APP_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from jarvis_backend.orchestrator import Orchestrator
from jarvis_backend.ui.cli import CLI


def main():
    print("Local Assistant started")
    print("Type 'exit' to quit.\n")

    orchestrator = Orchestrator()
    ui = CLI()

    while True:
        user_input = ui.get_input()
        if user_input.lower() in ("exit", "quit"):
            print("Goodbye.")
            break

        response = orchestrator.handle_input(user_input)
        ui.show_output(response)


if __name__ == "__main__":
    main()
