from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List
from uuid import uuid4
from openai import OpenAI
from supabase import create_client, Client
from pydantic_settings import BaseSettings, SettingsConfigDict
from datetime import datetime
import json
import asyncio
import os

# -------- Config & Env --------
class Settings(BaseSettings):
    app_name: str = "SnapBite"
    supabase_url: str
    supabase_key: str
    openai_api_key: str
    max_images: int = 5
    storage_bucket: str = "meal-images"
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

# -------- Supabase File Upload --------
async def save_file_to_supabase(file: UploadFile, user_id: int) -> str:
    ext = os.path.splitext(file.filename)[1] or ".jpg"
    filename = f"{user_id}_{datetime.utcnow().isoformat()}_{uuid4().hex}{ext}"
    file_data = await file.read()

    response = supabase.storage.from_(settings.storage_bucket).upload(
        path=filename,
        file=file_data,
        file_options={"content-type": file.content_type}
    )

    if hasattr(response, "error") and response.error:
        raise HTTPException(status_code=500, detail=f"Supabase upload failed: {response.error.message}")

    return supabase.storage.from_(settings.storage_bucket).get_public_url(filename)

# -------- Whisper Transcription --------
async def transcribe_audio(audio_file: UploadFile) -> str:
    temp_path = f"/tmp/{uuid4().hex}_{audio_file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await audio_file.read())

    with open(temp_path, "rb") as f:
        transcript = openai_client.audio.transcriptions.create(
            file=f,
            model="whisper-1"
        )

    os.remove(temp_path)
    return transcript.text

# -------- GPT-4.1 Vision with Audio --------
async def analyze_images_with_retries(image_urls: List[str], audio_text: str = "", retries: int = 2) -> dict:
    for attempt in range(retries + 1):
        try:
            # 🔊 Audio transcript injected here
            content_payload = [
                {
                    "type": "input_text",
                    "text": (
                        f"You're a nutritionist AI. Use the transcript and food image(s) to estimate nutritional content in JSON:\n"
                        "{ \"description\": \"...\", \"calories\": 500, \"protein\": 40, \"fat\": 20, \"carbs\": 50, \"confidence\": 0.9 }\n\n"
                        f"Transcript: \"{audio_text}\""
                    )
                }
            ] + [
                {
                    "type": "input_image",
                    "image_url": url
                }
                for url in image_urls
            ]

            response = openai_client.responses.create(
                model="gpt-4.1",
                input=[{"role": "user", "content": content_payload}],
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
    audio: UploadFile = File(...)
):
    if len(images) == 0:
        raise HTTPException(status_code=400, detail="At least 1 image is required.")
    if len(images) > settings.max_images:
        raise HTTPException(status_code=400, detail=f"Maximum {settings.max_images} images allowed.")

    try:
        # Upload all images to Supabase Storage
        image_urls = [await save_file_to_supabase(file, user_id) for file in images]

        # Transcribe audio
        audio_text = await transcribe_audio(audio)

        # Analyze with GPT Vision + audio
        ai_data = await analyze_images_with_retries(image_urls, audio_text)

        # Validate expected fields
        required = ["description", "calories", "protein", "fat", "carbs"]
        for key in required:
            if key not in ai_data:
                raise ValueError(f"Missing `{key}` in AI response.")

        # Insert into Supabase DB
        supabase.table("food_log").insert({
            "user_id": user_id,
            "estimated_calories": int(ai_data["calories"]),
            "protein_grams": int(ai_data["protein"]),
            "fat_grams": int(ai_data["fat"]),
            "carbs_grams": int(ai_data["carbs"]),
            "ai_description": ai_data["description"],
            "ai_confidence": float(ai_data.get("confidence", 0.9)),
            "image_urls": image_urls,
            "audio_transcript": audio_text,
        }).execute()

        return {
            "message": "Meal logged successfully ✅",
            "user_id": user_id,
            "calories": int(ai_data["calories"]),
            "protein_grams": int(ai_data["protein"]),
            "ai_result": ai_data,
            "image_urls": image_urls,
            "transcript": audio_text
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
