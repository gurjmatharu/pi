from fastapi import FastAPI
import uvicorn
import os
from supabase import create_client, Client, SupabaseException
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Awesome API"
    supabase_url: str
    supabase_key: str
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()

supabase: Client = create_client(settings.supabase_url, settings.supabase_key)
app = FastAPI()

@app.get("/")
async def root():
    try:
        # Replace 'users' with any existing table in your Supabase project
        response = supabase.table("users").select("*").limit(1).execute()
        if response.data is not None:
            print(response.data)
            return {"message": "Supabase connection successful", "data_sample": response.data}
        else:
            return {"message": "Connected, but no data returned from table."}
    except SupabaseException as e:
        return {"error": "Supabase query failed", "details": str(e)}
    except Exception as e:
        return {"error": "General failure", "details": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
