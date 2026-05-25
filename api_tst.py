
import os
from dotenv import load_dotenv
load_dotenv()
from google import genai
from pinecone import Pinecone
import uuid
import os
from google.genai import types



client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
chat = client.chats.create(model='gemini-3.5-flash')
response = chat.send_message('hi')
print(response.text)
  