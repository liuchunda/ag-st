from openai import OpenAI
import os 
from dotenv import load_dotenv

load_dotenv(override=True)

clientOpenAI = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL")
    )
response = clientOpenAI.chat.completions.create(
    model=os.getenv("OPENAI_MODEL"),
    messages=[
        {"role": "user", "content": "你好"}
    ]
)
print(response.choices[0].message.content)