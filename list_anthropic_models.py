import os
import anthropic

def list_models():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Please export ANTHROPIC_API_KEY first.")
        return
        
    client = anthropic.Anthropic(api_key=api_key)
    try:
        models = client.models.list()
        print("\nAvailable Models:")
        for m in models.data:
            print(f"- {m.id}")
    except Exception as e:
        print(f"Failed to list models: {e}")

if __name__ == "__main__":
    list_models()
