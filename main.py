import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Video

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple storage directory for uploaded files
STORAGE_DIR = "uploads"
os.makedirs(STORAGE_DIR, exist_ok=True)

@app.get("/")
def read_root():
    return {"message": "YouTube-like backend running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "❌ Unknown"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response

@app.post("/api/videos", response_model=dict)
async def upload_video(file: UploadFile = File(...), title: Optional[str] = None, description: Optional[str] = None, tags: Optional[str] = None):
    """
    Upload a video file and store metadata in database.
    - Saves the file under uploads/
    - Stores metadata (title, description, tags, size, content_type)
    """
    if file.content_type is None or not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Only video files are allowed")

    # Create a safe filename
    safe_name = f"{ObjectId()}{os.path.splitext(file.filename or '')[1]}"
    destination = os.path.join(STORAGE_DIR, safe_name)

    # Save file
    content = await file.read()
    with open(destination, "wb") as f:
        f.write(content)

    tag_list = [t.strip() for t in (tags or "").split(",") if t.strip()]

    video_doc = Video(
        title=title or (file.filename or "Untitled"),
        description=description,
        filename=safe_name,
        content_type=file.content_type,
        size=len(content),
        tags=tag_list,
    )

    inserted_id = create_document("video", video_doc)
    return {"id": inserted_id}

@app.get("/api/videos", response_model=List[dict])
async def list_videos(q: Optional[str] = None):
    """List videos with optional basic search in title/description/tags"""
    filter_dict = {}
    if q:
        # Basic case-insensitive partial search using $or
        regex = {"$regex": q, "$options": "i"}
        filter_dict = {"$or": [{"title": regex}, {"description": regex}, {"tags": regex}]}

    docs = get_documents("video", filter_dict=filter_dict)
    # Map to simple response
    results = []
    for d in docs:
        d["id"] = str(d.pop("_id")) if "_id" in d else None
        # Don't expose internal fields excessively
        results.append({
            "id": d.get("id"),
            "title": d.get("title"),
            "description": d.get("description"),
            "filename": d.get("filename"),
            "content_type": d.get("content_type"),
            "size": d.get("size"),
            "views": d.get("views", 0),
            "tags": d.get("tags", []),
            "created_at": d.get("created_at"),
        })
    return results

@app.get("/api/videos/{video_id}", response_model=dict)
async def get_video(video_id: str):
    from pymongo import ReturnDocument
    try:
        _id = ObjectId(video_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid video id")

    doc = db["video"].find_one_and_update(
        {"_id": _id},
        {"$inc": {"views": 1}, "$set": {"updated_at": None}},
        return_document=ReturnDocument.AFTER,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Video not found")

    return {
        "id": str(doc["_id"]),
        "title": doc.get("title"),
        "description": doc.get("description"),
        "filename": doc.get("filename"),
        "content_type": doc.get("content_type"),
        "size": doc.get("size"),
        "views": doc.get("views", 0),
        "tags": doc.get("tags", []),
        "created_at": doc.get("created_at"),
    }

@app.get("/stream/{filename}")
async def stream_file(filename: str):
    """Serve the raw video file for the frontend <video> player"""
    path = os.path.join(STORAGE_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, media_type="application/octet-stream")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
