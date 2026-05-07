# assistant/ui/cli.py
class CLI:
    def get_input(self) -> str:
        return input("\nYou: ")

    def show_output(self, text: str):
        print(f"\nAssistant: {text}")
