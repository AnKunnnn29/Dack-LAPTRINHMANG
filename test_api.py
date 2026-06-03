"""Small helper to test OpenAI/OpenRouter API configuration."""

import os


# MARK: Load environment variables from .env.
try:
    from dotenv import load_dotenv

    load_dotenv()
    print("[OK] Loaded .env file")
except ImportError:
    print("[WARN] python-dotenv is not installed; using system environment variables")


# MARK: Read report-generation config.
api_key = os.getenv("OPENAI_API_KEY")
model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
base_url = os.getenv("OPENAI_BASE_URL", "").strip()

masked_key = "NOT FOUND"
if api_key and len(api_key) > 24:
    masked_key = f"{api_key[:20]}...{api_key[-4:]}"

print("\nConfiguration:")
print(f"   API Key: {masked_key}")
print(f"   Model: {model}")
print(f"   Base URL: {base_url if base_url else 'Default OpenAI endpoint'}")

if not api_key or api_key == "your_api_key_here":
    print("\n[ERROR] API key not found or invalid.")
    print("        Please check your .env file.")
    raise SystemExit(1)


# MARK: Test one tiny chat completion.
print("\nTesting API connection...")
try:
    from openai import OpenAI

    client = OpenAI(base_url=base_url) if base_url else OpenAI()

    response = client.chat.completions.create(
        model=model,
        temperature=0.2,
        max_tokens=50,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant.",
            },
            {
                "role": "user",
                "content": "Say: API test successful.",
            },
        ],
    )

    result = response.choices[0].message.content.strip()
    print("\n[OK] API test successful.")
    print(f"   Response: {result}")
    print(f"   Model used: {response.model}")
    print(f"   Tokens used: {response.usage.total_tokens}")

except ImportError:
    print("\n[ERROR] OpenAI library is not installed.")
    print("        Run: pip install openai")
    raise SystemExit(1)
except Exception as exc:
    print("\n[ERROR] API test failed.")
    print(f"        Error: {exc}")
    raise SystemExit(1)
