from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List
from uuid import uuid4
import base64
import os
from openai import OpenAI
from supabase import create_client, Client
from pydantic_settings import BaseSettings, SettingsConfigDict
from datetime import datetime
import json
import asyncio

# -------- Config & Env --------
class Settings(BaseSettings):
    app_name: str = "SnapBite"
    supabase_url: str
    supabase_key: str
    openai_api_key: str
    max_images: int = 5
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
supabase: Client = create_client(settings.supabase_url, settings.supabase_key)
openai_client = OpenAI(api_key=settings.openai_api_key)

app = FastAPI()

# -------- Auth --------
BEARER_TOKENS = {
    "Gurjeet": 1,
}
bearer_scheme = HTTPBearer()

def get_user_id(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> int:
    token = credentials.credentials
    user_id = BEARER_TOKENS.get(token)
    if not user_id:
        raise HTTPException(status_code=403, detail="Invalid token")
    return user_id

# -------- File I/O --------
UPLOAD_FOLDER = "./uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

async def save_file_to_disk(file: UploadFile, user_id: int) -> str:
    ext = os.path.splitext(file.filename)[1] or ".jpg"
    filename = f"{user_id}_{datetime.utcnow().isoformat()}_{uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)
    return filepath

def encode_image(file_path: str) -> str:
    with open(file_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

# -------- GPT-4.1 Vision --------
async def analyze_images_with_retries(image_paths: List[str], retries: int = 2) -> dict:
    for attempt in range(retries + 1):
        try:
            content_payload = [
                {
                    "type": "input_text",
                    "text": (
                        f"You're a nutritionist AI. From these {len(image_paths)} food image(s), return a JSON object:\n"
                        "{ \"description\": \"...\", \"calories\": 500, \"protein\": 40, \"fat\": 20, \"carbs\": 50, \"confidence\": 0.9 }"
                    )
                }
            ] + [
                {
                    "type": "input_image",
                    "image_url": f"data:image/jpeg;base64,{encode_image(path)}"
                }
                for path in image_paths
            ]

            response = openai_client.responses.create(
                model="gpt-4.1",
                input=[
                    {
                        "role": "user",
                        "content": content_payload
                    }
                ],
            )

            raw_output = response.output_text
            json_start = raw_output.find('{')
            json_end = raw_output.rfind('}') + 1
            if json_start == -1 or json_end == -1:
                raise ValueError("Could not find JSON in GPT output_text.")
            return json.loads(raw_output[json_start:json_end])

        except Exception as e:
            if attempt < retries:
                await asyncio.sleep(1)
            else:
                raise HTTPException(status_code=500, detail=f"OpenAI failed after retries: {str(e)}")

# -------- API --------
@app.post("/log-meal")
async def log_meal(
    user_id: int = Depends(get_user_id),
    images: List[UploadFile] = File(...),
):
    if len(images) == 0:
        raise HTTPException(status_code=400, detail="At least 1 image is required.")
    if len(images) > settings.max_images:
        raise HTTPException(status_code=400, detail=f"Maximum {settings.max_images} images allowed.")

    try:
        # Save all images to disk
        image_paths = [await save_file_to_disk(file, user_id) for file in images]

        # Analyze with GPT Vision using latest format
        ai_data = await analyze_images_with_retries(image_paths)

        # Validate expected fields
        required = ["description", "calories", "protein", "fat", "carbs"]
        for key in required:
            if key not in ai_data:
                raise ValueError(f"Missing `{key}` in AI response.")

        # Insert into Supabase
        supabase.table("food_log").insert({
            "user_id": user_id,
            "estimated_calories": int(ai_data["calories"]),
            "protein_grams": int(ai_data["protein"]),
            "fat_grams": int(ai_data["fat"]),
            "carbs_grams": int(ai_data["carbs"]),
            "ai_description": ai_data["description"],
            "ai_confidence": float(ai_data.get("confidence", 0.9)),
            "image_urls": image_paths,
        }).execute()

        return {
            "message": "Meal logged successfully ✅",
            "user_id": user_id,
            "calories": int(ai_data["calories"]),
            "protein_grams": int(ai_data["protein"]),
            "ai_result": ai_data,
            "image_paths": image_paths
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
