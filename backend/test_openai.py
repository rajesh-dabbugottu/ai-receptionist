import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError("OPENAI_API_KEY is missing from backend/.env")

print("API key loaded successfully.")
print("Key starts with:", api_key[:7])

client = OpenAI(api_key=api_key)

try:
    response = client.responses.create(
        model="gpt-5-mini",
        input="Reply with exactly: OpenAI connection is working."
    )

    print("OpenAI response:")
    print(response.output_text)

except Exception as error:
    print("OpenAI test failed.")
    print("Error type:", type(error).__name__)
    print("Error details:", str(error))