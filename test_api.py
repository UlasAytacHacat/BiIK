import os
import httpx
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# SSL doğrulamayı atlayan bir istemci oluşturuyoruz
http_client = httpx.Client(verify=False) 

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    http_client=http_client
)

try:
    print("SSL Atlatılarak test ediliyor...")
    response = client.chat.completions.create(
      model="gpt-4o-mini",
      messages=[{"role": "user", "content": "Selam"}],
      timeout=15
    )
    print("BAŞARILI! Cevap:", response.choices[0].message.content)
except Exception as e:
    print(f"\n--- YİNE HATA --- \n{e}")