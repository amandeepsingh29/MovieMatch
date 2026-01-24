from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, HTTPException
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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

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

class CreateRoomRequest(BaseModel):
    username: str

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

# Mock movie data
MOVIES = [
    {"id": "1", "title": "The Shawshank Redemption", "year": 1994, "poster": "https://image.tmdb.org/t/p/w500/q6y0Go1tsGEsmtFryDOJo3dEmqu.jpg", "trailer": "6hB3S9bIaco", "genre": "Drama"},
    {"id": "2", "title": "The Godfather", "year": 1972, "poster": "https://image.tmdb.org/t/p/w500/3bhkrj58Vtu7enYsRolD1fZdja1.jpg", "trailer": "sY1S34973zA", "genre": "Crime"},
    {"id": "3", "title": "The Dark Knight", "year": 2008, "poster": "https://image.tmdb.org/t/p/w500/qJ2tW6WMUDux911r6m7haRef0WH.jpg", "trailer": "EXeTwQWrcwY", "genre": "Action"},
    {"id": "4", "title": "Pulp Fiction", "year": 1994, "poster": "https://image.tmdb.org/t/p/w500/d5iIlFn5s0ImszYzBPb8JPIfbXD.jpg", "trailer": "s7EdQ4FqbhY", "genre": "Crime"},
    {"id": "5", "title": "Forrest Gump", "year": 1994, "poster": "https://image.tmdb.org/t/p/w500/saHP97rTPS5eLmrLQEcANmKrsFl.jpg", "trailer": "bLvqoHBptjg", "genre": "Drama"},
    {"id": "6", "title": "Inception", "year": 2010, "poster": "https://image.tmdb.org/t/p/w500/ljsZTbVsrQSqZgWeep2B1QiDKuh.jpg", "trailer": "YoHD9XEInc0", "genre": "Sci-Fi"},
    {"id": "7", "title": "Fight Club", "year": 1999, "poster": "https://image.tmdb.org/t/p/w500/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg", "trailer": "qtRKdVHc-cE", "genre": "Drama"},
    {"id": "8", "title": "The Matrix", "year": 1999, "poster": "https://image.tmdb.org/t/p/w500/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg", "trailer": "vKQi3bBA1y8", "genre": "Sci-Fi"},
    {"id": "9", "title": "Interstellar", "year": 2014, "poster": "https://image.tmdb.org/t/p/w500/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg", "trailer": "zSWdZVtXT7E", "genre": "Sci-Fi"},
    {"id": "10", "title": "Parasite", "year": 2019, "poster": "https://image.tmdb.org/t/p/w500/7IiTTgloJzvGI1TAYymCfbfl3vT.jpg", "trailer": "5xH0HfJHsaY", "genre": "Thriller"},
]

def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@api_router.post("/rooms/create")
async def create_room(request: CreateRoomRequest):
    room_code = generate_room_code()
    
    # Check if code already exists
    existing = await db.rooms.find_one({"code": room_code}, {"_id": 0})
    while existing:
        room_code = generate_room_code()
        existing = await db.rooms.find_one({"code": room_code}, {"_id": 0})
    
    user_id = str(uuid.uuid4())
    member = Member(
        user_id=user_id,
        username=request.username,
        joined_at=datetime.now(timezone.utc).isoformat()
    )
    
    room = Room(
        code=room_code,
        created_at=datetime.now(timezone.utc).isoformat(),
        members=[member],
        status="waiting"
    )
    
    await db.rooms.insert_one(room.model_dump())
    
    return {"room_code": room_code, "user_id": user_id, "username": request.username}

@api_router.post("/rooms/join")
async def join_room(request: JoinRoomRequest):
    room = await db.rooms.find_one({"code": request.room_code}, {"_id": 0})
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    user_id = str(uuid.uuid4())
    member = Member(
        user_id=user_id,
        username=request.username,
        joined_at=datetime.now(timezone.utc).isoformat()
    )
    
    await db.rooms.update_one(
        {"code": request.room_code},
        {"$push": {"members": member.model_dump()}}
    )
    
    # Notify room members
    await manager.send_to_room({
        "type": "member_joined",
        "username": request.username,
        "user_id": user_id
    }, request.room_code)
    
    return {"room_code": request.room_code, "user_id": user_id, "username": request.username}

@api_router.get("/rooms/{room_code}")
async def get_room(room_code: str):
    room = await db.rooms.find_one({"code": room_code}, {"_id": 0})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room

@api_router.post("/rooms/start")
async def start_swiping(request: StartSwipingRequest):
    await db.rooms.update_one(
        {"code": request.room_code},
        {"$set": {"status": "swiping"}}
    )
    
    await manager.send_to_room({
        "type": "room_started"
    }, request.room_code)
    
    return {"status": "success"}

@api_router.get("/movies")
async def get_movies():
    return MOVIES

@api_router.post("/swipe")
async def record_swipe(swipe: SwipeRequest):
    # Store swipe
    swipe_doc = {
        "room_code": swipe.room_code,
        "user_id": swipe.user_id,
        "movie_id": swipe.movie_id,
        "direction": swipe.direction,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.swipes.insert_one(swipe_doc)
    
    # Check for match if it's a like
    if swipe.direction == "like":
        room = await db.rooms.find_one({"code": swipe.room_code}, {"_id": 0})
        if room:
            member_count = len(room["members"])
            
            # Count likes for this movie in this room
            likes = await db.swipes.count_documents({
                "room_code": swipe.room_code,
                "movie_id": swipe.movie_id,
                "direction": "like"
            })
            
            # If all members liked it, it's a match!
            if likes == member_count:
                # Check if match already exists
                existing_match = await db.matches.find_one({
                    "room_code": swipe.room_code,
                    "movie_id": swipe.movie_id
                }, {"_id": 0})
                
                if not existing_match:
                    match_doc = {
                        "room_code": swipe.room_code,
                        "movie_id": swipe.movie_id,
                        "matched_at": datetime.now(timezone.utc).isoformat()
                    }
                    await db.matches.insert_one(match_doc)
                    
                    # Get movie details
                    movie = next((m for m in MOVIES if m["id"] == swipe.movie_id), None)
                    
                    # Notify all room members
                    await manager.send_to_room({
                        "type": "match",
                        "movie": movie
                    }, swipe.room_code)
    
    return {"status": "success"}

@api_router.get("/matches/{room_code}")
async def get_matches(room_code: str):
    matches = await db.matches.find({"room_code": room_code}, {"_id": 0}).to_list(100)
    
    # Enrich with movie details
    for match in matches:
        movie = next((m for m in MOVIES if m["id"] == match["movie_id"]), None)
        match["movie"] = movie
    
    return matches

@app.websocket("/ws/{room_code}")
async def websocket_endpoint(websocket: WebSocket, room_code: str):
    await manager.connect(websocket, room_code)
    try:
        while True:
            data = await websocket.receive_text()
            # Keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_code)

app.include_router(api_router)

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