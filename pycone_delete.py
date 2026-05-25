# pip install "pinecone[grpc]"
import os
from dotenv import load_dotenv
load_dotenv()

from pinecone.grpc import PineconeGRPC as Pinecone

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))

index.delete(delete_all=True)