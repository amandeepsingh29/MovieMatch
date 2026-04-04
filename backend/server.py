from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import random
import string
import json
from urllib.parse import quote_plus, urlencode
from urllib.request import Request, urlopen

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")
SUPPORTED_LANGUAGES = ["English", "Hindi", "Punjabi"]

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_code: str):
        await websocket.accept()
        if room_code not in self.active_connections:
            self.active_connections[room_code] = []
        self.active_connections[room_code].append(websocket)

    def disconnect(self, websocket: WebSocket, room_code: str):
        if room_code in self.active_connections:
            if websocket in self.active_connections[room_code]:
                self.active_connections[room_code].remove(websocket)
            if not self.active_connections[room_code]:
                del self.active_connections[room_code]

    async def send_to_room(self, message: dict, room_code: str):
        if room_code in self.active_connections:
            for connection in self.active_connections[room_code]:
                try:
                    await connection.send_json(message)
                except:
                    pass

manager = ConnectionManager()

# Models
class Member(BaseModel):
    user_id: str
    username: str
    joined_at: str

class Room(BaseModel):
    code: str
    created_at: str
    members: List[Member] = []
    status: str = "waiting"
    include_adult: bool = False

class CreateRoomRequest(BaseModel):
    username: str
    include_adult: bool = False

class JoinRoomRequest(BaseModel):
    username: str
    room_code: str

class SwipeRequest(BaseModel):
    room_code: str
    user_id: str
    movie_id: str
    direction: str

class StartSwipingRequest(BaseModel):
    room_code: str


class GenrePreferencesRequest(BaseModel):
    room_code: str
    user_id: str
    genres: List[str]
    languages: List[str] = []
    eras: List[str] = []

# TMDB Configuration
import asyncio

TMDB_GENRES = {
    "Action": "28", "Adventure": "12", "Animation": "16", "Comedy": "35",
    "Crime": "80", "Drama": "18", "Fantasy": "14", "Romance": "10749",
    "Sci-Fi": "878", "Thriller": "53"
}
TMDB_LANGUAGES = {"English": "en", "Hindi": "hi", "Punjabi": "pa"}
SUPPORTED_ERAS = ["Classic", "2000s", "2010s+"]
REVERSE_GENRES = {v: k for k, v in TMDB_GENRES.items()}
REVERSE_LANGUAGES = {v: k for k, v in TMDB_LANGUAGES.items()}

def get_tmdb_api_key():
    return os.environ.get("TMDB_API_KEY")

def build_poster_fallback(title: str) -> str:
    return f"https://placehold.co/600x900/101010/ffffff/png?text={quote_plus(title)}"

async def fetch_tmdb_movies(genres: list[str], languages: list[str], page: int = 1, include_adult: bool = False) -> list[dict]:
    api_key = get_tmdb_api_key()
    if not api_key:
        logger.error("No TMDB_API_KEY set.")
        return []

    # Map genres to TMDB IDs
    genre_ids = [TMDB_GENRES[g] for g in genres if g in TMDB_GENRES]
    
    # Map languages to TMDB ISO codes
    lang_codes = [TMDB_LANGUAGES[l] for l in languages if l in TMDB_LANGUAGES]
    
    query = {
        "api_key": api_key,
        "page": page,
        "sort_by": "popularity.desc",
        "include_adult": "true" if include_adult else "false"  # Explicitly filters out pornographic/adult-only content
    }
    
    if genre_ids:
        query["with_genres"] = "|".join(genre_ids)
    if lang_codes:
        query["with_original_language"] = "|".join(lang_codes)

    endpoint = f"https://api.themoviedb.org/3/discover/movie?{urlencode(query)}"

    def _fetch():
        req = Request(endpoint, headers={"User-Agent": "MovieMatch/1.0"})
        with urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8")).get("results", [])
            
    try:
        results = await asyncio.to_thread(_fetch)
    except Exception as e:
        logger.error(f"Failed to fetch from TMDB: {e}")
        return []
        
    movies = []
    for m in results:
        title = m.get("title") or m.get("original_title") or "Unknown"
        year = int(m.get("release_date", "0")[:4]) if m.get("release_date") else 0
        poster_path = m.get("poster_path")
        poster = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else build_poster_fallback(title)
        
        # Best guess mapping for genre and language
        primary_genre = "Drama"
        if m.get("genre_ids"):
            primary_genre = REVERSE_GENRES.get(str(m.get("genre_ids")[0]), "Drama")
            
        lang = REVERSE_LANGUAGES.get(m.get("original_language", "en"), "English")

        movies.append({
            "id": str(m.get("id")),
            "title": title,
            "year": year,
            "poster": poster,
            "genre": primary_genre,
            "language": lang,
            "trailer_url": f"https://www.youtube.com/results?search_query={quote_plus(title)}+official+trailer"
        })
        
    return movies

async def fetch_movie_by_id(movie_id: str) -> dict:
    api_key = get_tmdb_api_key()
    if not api_key:
        return {}
        
    endpoint = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}"
    
    def _fetch():
        req = Request(endpoint, headers={"User-Agent": "MovieMatch/1.0"})
        with urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
            
    try:
        m = await asyncio.to_thread(_fetch)
        title = m.get("title", "")
        poster_path = m.get("poster_path")
        return {
            "id": str(m.get("id")),
            "title": title,
            "year": int(m.get("release_date", "0")[:4]) if m.get("release_date") else 0,
            "poster": f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else build_poster_fallback(title)
        }
    except Exception:
        return {}




def year_to_era(year: int) -> str:
    if year < 2000:
        return "Classic"
    if year < 2010:
        return "2000s"
    return "2010s+"

def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@api_router.post("/rooms/create")
async def create_room(request: CreateRoomRequest):
    username = request.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")

    room_code = generate_room_code()
    
    # Check if code already exists
    existing = await db.rooms.find_one({"code": room_code}, {"_id": 0})
    while existing:
        room_code = generate_room_code()
        existing = await db.rooms.find_one({"code": room_code}, {"_id": 0})
    
    user_id = str(uuid.uuid4())
    member = Member(
        user_id=user_id,
        username=username,
        joined_at=datetime.now(timezone.utc).isoformat()
    )
    
    room = Room(
        code=room_code,
        created_at=datetime.now(timezone.utc).isoformat(),
        members=[member],
        status="waiting",
        include_adult=request.include_adult
    )
    
    await db.rooms.insert_one(room.model_dump())
    
    return {"room_code": room_code, "user_id": user_id, "username": username}

@api_router.post("/rooms/join")
async def join_room(request: JoinRoomRequest):
    username = request.username.strip()
    room_code = request.room_code.strip().upper()

    if not username:
        raise HTTPException(status_code=400, detail="Username is required")

    room = await db.rooms.find_one({"code": room_code}, {"_id": 0})
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.get("status") != "waiting":
        raise HTTPException(status_code=400, detail="Swiping already started")
    
    user_id = str(uuid.uuid4())
    member = Member(
        user_id=user_id,
        username=username,
        joined_at=datetime.now(timezone.utc).isoformat()
    )
    
    await db.rooms.update_one(
        {"code": room_code},
        {"$push": {"members": member.model_dump()}}
    )
    
    # Notify room members
    await manager.send_to_room({
        "type": "member_joined",
        "username": username,
        "user_id": user_id
    }, room_code)
    
    return {"room_code": room_code, "user_id": user_id, "username": username}

@api_router.get("/rooms/{room_code}")
async def get_room(room_code: str):
    room = await db.rooms.find_one({"code": room_code}, {"_id": 0})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room

@api_router.post("/rooms/start")
async def start_swiping(request: StartSwipingRequest):
    room_code = request.room_code.strip().upper()
    room = await db.rooms.find_one({"code": room_code}, {"_id": 0})

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.get("status") == "swiping":
        # If users navigated back to waiting room, re-broadcast start so everyone can re-enter swipe view.
        await manager.send_to_room({
            "type": "room_started"
        }, room_code)
        return {"status": "success"}

    if len(room.get("members", [])) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 members to start")

    await db.rooms.update_one(
        {"code": room_code},
        {"$set": {"status": "swiping"}}
    )
    
    await manager.send_to_room({
        "type": "room_started"
    }, room_code)
    
    return {"status": "success"}

@api_router.get("/genres")
async def get_genres():
    return sorted(list(TMDB_GENRES.keys()))


@api_router.get("/languages")
async def get_languages():
    return SUPPORTED_LANGUAGES


@api_router.get("/eras")
async def get_eras():
    return SUPPORTED_ERAS


@api_router.get("/movies")
async def get_movies(genres: Optional[str] = Query(default=None)):
    parsed_genres = [g.strip() for g in genres.split(",")] if genres else []
    return await fetch_tmdb_movies(parsed_genres, list(TMDB_LANGUAGES.keys()), page=1)


@api_router.post("/rooms/preferences")
async def submit_genre_preferences(request: GenrePreferencesRequest):
    room_code = request.room_code.strip().upper()
    room = await db.rooms.find_one({"code": room_code}, {"_id": 0})

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    user_ids = {member.get("user_id") for member in room.get("members", [])}
    if request.user_id not in user_ids:
        raise HTTPException(status_code=403, detail="User is not a member of this room")

    cleaned_genres = sorted({genre.strip() for genre in request.genres if genre.strip()})
    cleaned_languages = sorted({language.strip() for language in request.languages if language.strip()})

    if not cleaned_genres:
        raise HTTPException(status_code=400, detail="Select at least one genre")
    if not cleaned_languages:
        raise HTTPException(status_code=400, detail="Select at least one language")

    valid_genres = set(TMDB_GENRES.keys())
    valid_languages = set(SUPPORTED_LANGUAGES)

    invalid = [genre for genre in cleaned_genres if genre not in valid_genres]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid genres: {', '.join(invalid)}")

    invalid_languages = [language for language in cleaned_languages if language not in valid_languages]
    if invalid_languages:
        raise HTTPException(status_code=400, detail=f"Invalid languages: {', '.join(invalid_languages)}")

    await db.rooms.update_one(
        {"code": room_code},
        {
            "$set": {
                f"genre_preferences.{request.user_id}": {
                    "genres": cleaned_genres,
                    "languages": cleaned_languages,
                }
            }
        },
    )

    await manager.send_to_room(
        {
            "type": "preferences_updated",
            "user_id": request.user_id,
        },
        room_code,
    )

    updated_room = await db.rooms.find_one({"code": room_code}, {"_id": 0})
    preferences = updated_room.get("genre_preferences", {})
    selected_members = len(preferences)
    total_members = len(updated_room.get("members", []))

    return {
        "status": "success",
        "selected_members": selected_members,
        "total_members": total_members,
    }


@api_router.get("/rooms/{room_code}/movies")
async def get_room_movies(room_code: str, page: int = Query(default=1)):
    normalized_code = room_code.strip().upper()
    room = await db.rooms.find_one({"code": normalized_code}, {"_id": 0})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    preferences = room.get("genre_preferences", {})
    total_members = len(room.get("members", []))
    selected_members = len(preferences)

    merged_genres = sorted(
        {
            genre
            for member_preferences in preferences.values()
            for genre in member_preferences.get("genres", [])
        }
    )
    merged_languages = sorted(
        {
            language
            for member_preferences in preferences.values()
            for language in member_preferences.get("languages", [])
        }
    )
    
    # Defaults if none selected yet
    query_genres = merged_genres if merged_genres else list(TMDB_GENRES.keys())
    query_languages = merged_languages if merged_languages else list(TMDB_LANGUAGES.keys())
    include_adult = room.get("include_adult", False)

    # Fetch dynamic batch from TMDB
    movies = await fetch_tmdb_movies(query_genres, query_languages, page=page, include_adult=include_adult)

    waiting_for = max(total_members - selected_members, 0)
    return {
        "movies": movies,
        "merged_genres": merged_genres,
        "merged_languages": merged_languages,
        "selected_members": selected_members,
        "total_members": total_members,
        "waiting_for": waiting_for,
    }

@api_router.post("/swipe")
async def record_swipe(swipe: SwipeRequest):
    room_code = swipe.room_code.strip().upper()
    direction = swipe.direction.strip().lower()
    if direction not in {"like", "dislike"}:
        raise HTTPException(status_code=400, detail="Direction must be 'like' or 'dislike'")

    room = await db.rooms.find_one({"code": room_code}, {"_id": 0})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.get("status") != "swiping":
        raise HTTPException(status_code=400, detail="Room is not in swiping state")

    user_ids = {member.get("user_id") for member in room.get("members", [])}
    if swipe.user_id not in user_ids:
        raise HTTPException(status_code=403, detail="User is not a member of this room")



    # Store swipe
    swipe_doc = {
        "room_code": room_code,
        "user_id": swipe.user_id,
        "movie_id": swipe.movie_id,
        "direction": direction,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    await db.swipes.update_one(
        {
            "room_code": room_code,
            "user_id": swipe.user_id,
            "movie_id": swipe.movie_id,
        },
        {"$set": swipe_doc},
        upsert=True,
    )
    
    # Check for match if it's a like
    if direction == "like":
        member_count = len(room["members"])

        # Count likes for this movie in this room
        likes = await db.swipes.count_documents({
            "room_code": room_code,
            "movie_id": swipe.movie_id,
            "direction": "like"
        })

        # If all members liked it, it's a match!
        if likes == member_count:
            # Check if match already exists
            existing_match = await db.matches.find_one({
                "room_code": room_code,
                "movie_id": swipe.movie_id
            }, {"_id": 0})

            if not existing_match:
                match_doc = {
                    "room_code": room_code,
                    "movie_id": swipe.movie_id,
                    "matched_at": datetime.now(timezone.utc).isoformat()
                }
                await db.matches.insert_one(match_doc)

                # Get movie details dynamically
                movie = await fetch_movie_by_id(swipe.movie_id)
                if movie:
                    await db.matches.update_one(
                        {"room_code": room_code, "movie_id": swipe.movie_id},
                        {"$set": {"movie_cache": movie}}
                    )

                # Notify all room members
                await manager.send_to_room({
                    "type": "match",
                    "movie": movie
                }, room_code)
    
    return {"status": "success"}

@api_router.get("/matches/{room_code}")
async def get_matches(room_code: str):
    matches = await db.matches.find({"room_code": room_code}, {"_id": 0}).to_list(100)
    
    for match in matches:
        if "movie_cache" in match:
            match["movie"] = match["movie_cache"]
        else:
            # Fallback if cached data not found
            match["movie"] = await fetch_movie_by_id(match["movie_id"])
            await db.matches.update_one(
                {"room_code": room_code, "movie_id": match["movie_id"]},
                {"$set": {"movie_cache": match["movie"]}}
            )
            
    return matches

@api_router.websocket("/ws/{room_code}")
async def websocket_endpoint(websocket: WebSocket, room_code: str):
    await manager.connect(websocket, room_code)
    try:
        while True:
            data = await websocket.receive_text()
            # Keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_code)

app.include_router(api_router)


@app.get("/")
async def root():
    return {
        "service": "MovieMatch Backend",
        "status": "ok",
        "docs": "/docs",
        "api_base": "/api",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()