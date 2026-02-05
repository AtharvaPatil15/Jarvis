# main.py
from assistant.orchestrator import Orchestrator
from assistant.ui.cli import CLI

def main():
    print("🟢 Local Assistant started (Phase 1)")
    print("Type 'exit' to quit.\n")

    orchestrator = Orchestrator()
    ui = CLI()

    while True:
        user_input = ui.get_input()
        if user_input.lower() in ("exit", "quit"):
            print("👋 Goodbye.")
            break

        response = orchestrator.handle_input(user_input)
        ui.show_output(response)

if __name__ == "__main__":
    main()
