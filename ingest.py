import os
from dotenv import load_dotenv
load_dotenv()
from google import genai
from pinecone import Pinecone
import uuid
import os
from google.genai import types




context = "\n".join([
    match["metadata"]["text"]
    for match in results["matches"]
])

prompt = f"""
Answer the question using the context below.

Context:
{context}

Question:
{query}
"""
chat = client.chats.create(model='gemini-3.5-flash')
for chunk in  chat.send_message_stream(prompt):
  print(chunk.text)