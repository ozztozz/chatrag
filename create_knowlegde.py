import os
from dotenv import load_dotenv
load_dotenv()
from google import genai
from pinecone import Pinecone
import uuid
import os
from google.genai import types
import json
with open("alpha_chat.json", "r", encoding="utf-8") as f:
    data = json.load(f)






pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


for item in data :
    chunk = client.models.embed_content(
                model="gemini-embedding-2",
                contents=item["content"],
                config=types.EmbedContentConfig(output_dimensionality=512)
            ).embeddings[0].values
    vector=[{
        "id": item["chunk_id"],
        "values": chunk,
        "metadata": {
            "keywords": item["keywords"],
            "content": item["content"],
            "category": item["category"],
            "sub_category": item["sub_category"]
        }
        }]
    index.upsert(vectors=vector)

print("Embedding stored successfully")