# assistant/brain/llm.py
import requests

class LocalLLM:
    def __init__(
        self,
        base_url="http://127.0.0.1:1234",
        model="qwen2.5-14b-instruct-1m"
    ):
        self.base_url = base_url
        self.model = model

    def generate(self, prompt: str) -> str:
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a calm, precise, helpful virtual assistant."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.4,
                "max_tokens": 512
            },
            timeout=120
        )

        # Debug helper (optional, remove later)
        if response.status_code != 200:
            print("LM Studio error:", response.text)

        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
