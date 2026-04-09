from supabase import create_client, Client
from dotenv import load_dotenv
import os

# Cargar las variables del archivo .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_products_from_supabase():
    try:
        response = supabase.table("perfumes").select("*").execute()
        return response.data
    except Exception as e:
        print(f"Error al obtener productos de Supabase: {e}")
        return []
