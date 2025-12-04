import os
from supabase import create_client, Client

url = os.getenv("SUPABASE_URL", "")
key = os.getenv("SUPABASE_SERVICE_KEY", "")

if not url or not key:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

supabase: Client = create_client(url, key)

