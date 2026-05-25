import os
from dotenv import load_dotenv
load_dotenv()
from google import genai
from pinecone import Pinecone
import uuid
import os
from google.genai import types

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


query = " çalışma saatleri nedir?"

query_embedding = client.models.embed_content(
    #model="gemini-embedding-2",
    model="gemini-3-flash",
    contents=query,
     config=types.EmbedContentConfig(output_dimensionality=512)
).embeddings[0].values


# Execute similarity search
search_results = index.query(
    
    vector=query_embedding,                # Your generated query embedding array
    top_k=4,                            # Number of closest matches to return
    include_metadata=True,              # Crucial for RAG to fetch raw text/keywords
    include_values=False                # Set False to save bandwidth (doesn't return raw vectors)
)



context = "\n".join([
    match["metadata"]["content"]
    for match in search_results["matches"]
])

prompt = f"""
Sen Alpha Academy Spor Kulübü’nün profesyonel, samimi ve güven veren temsilcisisin. 
Bot olduğunu belirt. 
- Samimi ama profesyonel konuş.
- Kısa, net ve güven veren cevaplar ver.Cevapla ilgili samimi emojiler kullan. Cevaplar 3 cümleyi geçmesin.
- “Kurs” değil “Spor Kulübü” ifadesini kullan.
- Her sporcunun özel olduğunu hissettir.
- Amacın, velileri bilgilendirmek. 
- Yeterince bilgi verdikten sonrayüz yüze görüşme için tesise davet etmektir.
- Randevuyu kabul ederse Sporcu ve veli adını iste.

Context:
{context}

Question:
{query}
"""
chat = client.chats.create(model='gemini-3.5-flash')
for chunk in  chat.send_message_stream(prompt):
  print(chunk.text)

