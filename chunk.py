import json
with open("alpha_chat.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for item in data:
    print(item["chunk_id"])