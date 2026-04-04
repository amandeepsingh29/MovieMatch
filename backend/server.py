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
from urllib.parse import quote_plus

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


class GenrePreferencesRequest(BaseModel):
    room_code: str
    user_id: str
    genres: List[str]
    languages: List[str] = []
    eras: List[str] = []

# Mock movie data
MOVIES = [
    {"id": "1", "title": "The Shawshank Redemption", "year": 1994, "poster": "https://image.tmdb.org/t/p/w500/q6y0Go1tsGEsmtFryDOJo3dEmqu.jpg", "trailer": "6hB3S9bIaco", "genre": "Drama", "language": "English"},
    {"id": "2", "title": "The Godfather", "year": 1972, "poster": "https://image.tmdb.org/t/p/w500/3bhkrj58Vtu7enYsRolD1fZdja1.jpg", "trailer": "sY1S34973zA", "genre": "Crime", "language": "English"},
    {"id": "3", "title": "The Dark Knight", "year": 2008, "poster": "https://image.tmdb.org/t/p/w500/qJ2tW6WMUDux911r6m7haRef0WH.jpg", "trailer": "EXeTwQWrcwY", "genre": "Action", "language": "English"},
    {"id": "4", "title": "Pulp Fiction", "year": 1994, "poster": "https://image.tmdb.org/t/p/w500/d5iIlFn5s0ImszYzBPb8JPIfbXD.jpg", "trailer": "s7EdQ4FqbhY", "genre": "Crime", "language": "English"},
    {"id": "5", "title": "Forrest Gump", "year": 1994, "poster": "https://image.tmdb.org/t/p/w500/saHP97rTPS5eLmrLQEcANmKrsFl.jpg", "trailer": "bLvqoHBptjg", "genre": "Drama", "language": "English"},
    {"id": "6", "title": "Inception", "year": 2010, "poster": "https://image.tmdb.org/t/p/w500/ljsZTbVsrQSqZgWeep2B1QiDKuh.jpg", "trailer": "YoHD9XEInc0", "genre": "Sci-Fi", "language": "English"},
    {"id": "7", "title": "Fight Club", "year": 1999, "poster": "https://image.tmdb.org/t/p/w500/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg", "trailer": "qtRKdVHc-cE", "genre": "Drama", "language": "English"},
    {"id": "8", "title": "The Matrix", "year": 1999, "poster": "https://image.tmdb.org/t/p/w500/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg", "trailer": "vKQi3bBA1y8", "genre": "Sci-Fi", "language": "English"},
    {"id": "9", "title": "Interstellar", "year": 2014, "poster": "https://image.tmdb.org/t/p/w500/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg", "trailer": "zSWdZVtXT7E", "genre": "Sci-Fi", "language": "English"},
    {"id": "10", "title": "Parasite", "year": 2019, "poster": "https://image.tmdb.org/t/p/w500/7IiTTgloJzvGI1TAYymCfbfl3vT.jpg", "trailer": "5xH0HfJHsaY", "genre": "Thriller", "language": "Korean"},
    {"id": "11", "title": "3 Idiots", "year": 2009, "poster": "https://media.themoviedb.org/t/p/w500/gmSRHU1Wtiatj8KoyVt8rT9ockx.jpg", "trailer": "K0eDlFX9GMc", "genre": "Drama", "language": "Hindi"},
    {"id": "12", "title": "Dangal", "year": 2016, "poster": "https://media.themoviedb.org/t/p/w500/1CoKNi3XVyijPCvy0usDbSWEXAg.jpg", "trailer": "x_7YlGv9u1g", "genre": "Drama", "language": "Hindi"},
    {"id": "13", "title": "Carry on Jatta", "year": 2012, "poster": "https://media.themoviedb.org/t/p/w500/3KJ8UiNloo0Un2osnQOuyXfqNO2.jpg", "trailer": "R8fP-C8H4vE", "genre": "Comedy", "language": "Punjabi"},
    {"id": "14", "title": "Ardaas", "year": 2016, "poster": "https://media.themoviedb.org/t/p/w500/ch6dE7bXJELXUM5QA48aoqx2ojH.jpg", "trailer": "l5tx7A2n7kQ", "genre": "Drama", "language": "Punjabi"},
    {"id": "15", "title": "The Lord of the Rings: The Fellowship of the Ring", "year": 2001, "poster": "https://image.tmdb.org/t/p/w500/6oom5QYQ2yQTMJIbnvbkBL9cHo6.jpg", "trailer": "V75dMMIW2B4", "genre": "Adventure", "language": "English"},
    {"id": "16", "title": "The Lord of the Rings: The Return of the King", "year": 2003, "poster": "https://image.tmdb.org/t/p/w500/rCzpDGLbOoPwLjy3OAm5NUPOTrC.jpg", "trailer": "r5X-hFf6Bwo", "genre": "Adventure", "language": "English"},
    {"id": "17", "title": "Gladiator", "year": 2000, "poster": "https://image.tmdb.org/t/p/w500/ty8TGRuvJLPUmAR1H1nRIsgwvim.jpg", "trailer": "owK1qxDselE", "genre": "Action", "language": "English"},
    {"id": "18", "title": "The Prestige", "year": 2006, "poster": "https://media.themoviedb.org/t/p/w500/rOa94QOq3wbqKBHjSqL0WtPPJm1.jpg", "trailer": "ijXruSzfGEc", "genre": "Thriller", "language": "English"},
    {"id": "19", "title": "Whiplash", "year": 2014, "poster": "https://image.tmdb.org/t/p/w500/7fn624j5lj3xTme2SgiLCeuedmO.jpg", "trailer": "7d_jQycdQGo", "genre": "Drama", "language": "English"},
    {"id": "20", "title": "Mad Max: Fury Road", "year": 2015, "poster": "https://image.tmdb.org/t/p/w500/hA2ple9q4qnwxp3hKVNhroipsir.jpg", "trailer": "hEJnMQG9ev8", "genre": "Action", "language": "English"},
    {"id": "21", "title": "Spider-Man: Into the Spider-Verse", "year": 2018, "poster": "https://image.tmdb.org/t/p/w500/iiZZdoQBEYBv6id8su7ImL0oCbD.jpg", "trailer": "g4Hbz2jLxvQ", "genre": "Animation", "language": "English"},
    {"id": "22", "title": "Coco", "year": 2017, "poster": "https://image.tmdb.org/t/p/w500/gGEsBPAijhVUFoiNpgZXqRVWJt2.jpg", "trailer": "Ga6RYejo6Hk", "genre": "Animation", "language": "English"},
    {"id": "23", "title": "Arrival", "year": 2016, "poster": "https://image.tmdb.org/t/p/w500/x2FJsf1ElAgr63Y3PNPtJrcmpoe.jpg", "trailer": "tFMo3UJ4B4g", "genre": "Sci-Fi", "language": "English"},
    {"id": "24", "title": "Blade Runner 2049", "year": 2017, "poster": "https://image.tmdb.org/t/p/w500/gajva2L0rPYkEWjzgFlBXCAVBE5.jpg", "trailer": "gCcx85zbxz4", "genre": "Sci-Fi", "language": "English"},
    {"id": "25", "title": "Shutter Island", "year": 2010, "poster": "https://image.tmdb.org/t/p/w500/kve20tXwUZpu4GUX8l6X7Z4jmL6.jpg", "trailer": "5iaYLCiq5RM", "genre": "Thriller", "language": "English"},
    {"id": "26", "title": "The Social Network", "year": 2010, "poster": "https://image.tmdb.org/t/p/w500/n0ybibhJtQ5icDqTp8eRytcIHJx.jpg", "trailer": "lB95KLmpLR4", "genre": "Drama", "language": "English"},
    {"id": "27", "title": "Zindagi Na Milegi Dobara", "year": 2011, "poster": "https://media.themoviedb.org/t/p/w500/hKO9O715wYxjkQSEv47giCYcyO8.jpg", "trailer": "FJrpcDgC3zU", "genre": "Comedy", "language": "Hindi"},
    {"id": "28", "title": "Andhadhun", "year": 2018, "poster": "https://media.themoviedb.org/t/p/w500/dy3K6hNvwE05siGgiLJcEiwgpdO.jpg", "trailer": "2iVYI99VGaw", "genre": "Thriller", "language": "Hindi"},
    {"id": "29", "title": "Gully Boy", "year": 2019, "poster": "https://media.themoviedb.org/t/p/w500/4RE7TD5TqEXbPKyUHcn7CSeMlrJ.jpg", "trailer": "JfbxcD6biOk", "genre": "Drama", "language": "Hindi"},
    {"id": "30", "title": "Bajrangi Bhaijaan", "year": 2015, "poster": "https://media.themoviedb.org/t/p/w500/ks1xKebubTgHgfzGDw77SAOiUJ8.jpg", "trailer": "4nwAra0mz_Q", "genre": "Drama", "language": "Hindi"},
    {"id": "31", "title": "Punjab 1984", "year": 2014, "poster": "https://media.themoviedb.org/t/p/w500/yJcg6qaDFok73SC353u4oEYpkvF.jpg", "trailer": "_Fu4ax6N45Y", "genre": "Drama", "language": "Punjabi"},
    {"id": "32", "title": "Jatt & Juliet", "year": 2012, "poster": "https://media.themoviedb.org/t/p/w500/sWheGtsztva6pVksRorg0mWC1M6.jpg", "trailer": "9mG0f9w9mYI", "genre": "Comedy", "language": "Punjabi", "imdb_url": "https://www.imdb.com/title/tt2196254/", "imdb_poster_url": "https://www.imdb.com/title/tt2196254/mediaviewer/rm4046382080/?ref_=tt_ov_i"},
    {"id": "33", "title": "Sufna", "year": 2020, "poster": "https://media.themoviedb.org/t/p/w500/ozso0mV2H6Yke5L6mgZnripGwez.jpg", "trailer": "W6S0h5f6g5M", "genre": "Romance", "language": "Punjabi"},
    {"id": "34", "title": "Train to Busan", "year": 2016, "poster": "https://image.tmdb.org/t/p/w500/3H1WFCuxyNRP35oiL2qqwhAXxc0.jpg", "trailer": "pyWuHv2-Abk", "genre": "Thriller", "language": "Korean"},
    {"id": "35", "title": "Oldboy", "year": 2003, "poster": "https://image.tmdb.org/t/p/w500/pWDtjs568ZfOTMbURQBYuT4Qxka.jpg", "trailer": "2HkjrJ6IK5E", "genre": "Thriller", "language": "Korean"},
    {"id": "36", "title": "Memories of Murder", "year": 2003, "poster": "https://media.themoviedb.org/t/p/w500/dsEoTJKM1s5OVDkS2P2JdoTxo4K.jpg", "trailer": "0n_HQwQU8ls", "genre": "Crime", "language": "Korean"},
    {"id": "37", "title": "Your Name", "year": 2016, "poster": "https://image.tmdb.org/t/p/w500/q719jXXEzOoYaps6babgKnONONX.jpg", "trailer": "xU47nhruN-Q", "genre": "Animation", "language": "Japanese"},
    {"id": "38", "title": "Spirited Away", "year": 2001, "poster": "https://image.tmdb.org/t/p/w500/39wmItIWsg5sZMyRUHLkWBcuVCM.jpg", "trailer": "ByXuk9QqQkk", "genre": "Animation", "language": "Japanese"},
    {"id": "39", "title": "The Intouchables", "year": 2011, "poster": "https://image.tmdb.org/t/p/w500/323BP0itpxTsO0skTwdnVmf7YC9.jpg", "trailer": "34WIbmXkewU", "genre": "Comedy", "language": "French"},
    {"id": "40", "title": "Pan's Labyrinth", "year": 2006, "poster": "https://media.themoviedb.org/t/p/w500/z7xXihu5wHuSMWymq5VAulPVuvg.jpg", "trailer": "EqYiSlkvRuw", "genre": "Fantasy", "language": "Spanish"},
]


def expand_movies_by_genre(movies: List[dict], min_per_genre: int = 100) -> List[dict]:
    grouped: dict[str, List[dict]] = {}
    for movie in movies:
        grouped.setdefault(movie["genre"], []).append(movie)

    expanded = list(movies)
    next_id = max(int(movie["id"]) for movie in movies) + 1

    for genre, seeds in grouped.items():
        if len(seeds) >= min_per_genre:
            continue

        needed = min_per_genre - len(seeds)
        for i in range(needed):
            seed = seeds[i % len(seeds)]
            variant_number = i + 1
            year_shift = (i % 17) - 8
            variant_year = max(1970, min(2025, seed["year"] + year_shift))

            variant = dict(seed)
            variant["id"] = str(next_id)
            variant["title"] = f"{seed['title']} Cut {variant_number}"
            variant["year"] = variant_year
            variant["trailer"] = ""
            variant.pop("imdb_url", None)
            variant.pop("imdb_poster_url", None)

            expanded.append(variant)
            next_id += 1

    return expanded


MOVIES = expand_movies_by_genre(MOVIES, min_per_genre=100)


def build_poster_fallback(title: str) -> str:
    return f"https://placehold.co/600x900/101010/ffffff/png?text={quote_plus(title)}"


# Ensure every movie has stable fallback assets.
for movie in MOVIES:
    movie["poster_fallback"] = build_poster_fallback(movie["title"])
    trailer_id = movie.get("trailer", "").strip()
    if trailer_id:
        movie["trailer_url"] = f"https://www.youtube.com/watch?v={trailer_id}&t=30s"
    else:
        movie["trailer_url"] = (
            "https://www.youtube.com/results?search_query="
            + quote_plus(f"{movie['title']} official trailer")
        )


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
        status="waiting"
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
    genres = sorted({movie["genre"] for movie in MOVIES})
    return genres


@api_router.get("/languages")
async def get_languages():
    languages = sorted({movie.get("language", "English") for movie in MOVIES})
    return languages


@api_router.get("/eras")
async def get_eras():
    return ["Classic", "2000s", "2010s+"]


@api_router.get("/movies")
async def get_movies(genres: Optional[str] = Query(default=None)):
    if not genres:
        return MOVIES

    genre_filter = {
        genre.strip().lower()
        for genre in genres.split(",")
        if genre.strip()
    }

    if not genre_filter:
        return MOVIES

    return [
        movie for movie in MOVIES if movie["genre"].strip().lower() in genre_filter
    ]


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
    cleaned_eras = sorted({era.strip() for era in request.eras if era.strip()})

    if not cleaned_genres:
        raise HTTPException(status_code=400, detail="Select at least one genre")
    if not cleaned_languages:
        raise HTTPException(status_code=400, detail="Select at least one language")
    if not cleaned_eras:
        raise HTTPException(status_code=400, detail="Select at least one era")

    valid_genres = {movie["genre"] for movie in MOVIES}
    valid_languages = {movie.get("language", "English") for movie in MOVIES}
    valid_eras = {"Classic", "2000s", "2010s+"}

    invalid = [genre for genre in cleaned_genres if genre not in valid_genres]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid genres: {', '.join(invalid)}")

    invalid_languages = [language for language in cleaned_languages if language not in valid_languages]
    if invalid_languages:
        raise HTTPException(status_code=400, detail=f"Invalid languages: {', '.join(invalid_languages)}")

    invalid_eras = [era for era in cleaned_eras if era not in valid_eras]
    if invalid_eras:
        raise HTTPException(status_code=400, detail=f"Invalid eras: {', '.join(invalid_eras)}")

    await db.rooms.update_one(
        {"code": room_code},
        {
            "$set": {
                f"genre_preferences.{request.user_id}": {
                    "genres": cleaned_genres,
                    "languages": cleaned_languages,
                    "eras": cleaned_eras,
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
async def get_room_movies(room_code: str):
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
    merged_eras = sorted(
        {
            era
            for member_preferences in preferences.values()
            for era in member_preferences.get("eras", [])
        }
    )

    if not merged_genres and not merged_languages and not merged_eras:
        movies = MOVIES
    else:
        merged_lookup = {genre.lower() for genre in merged_genres}
        merged_language_lookup = {language.lower() for language in merged_languages}
        merged_era_lookup = {era.lower() for era in merged_eras}
        movies = [
            movie
            for movie in MOVIES
            if (
                (not merged_lookup or movie["genre"].strip().lower() in merged_lookup)
                and (
                    not merged_language_lookup
                    or movie.get("language", "English").strip().lower()
                    in merged_language_lookup
                )
                and (
                    not merged_era_lookup
                    or year_to_era(movie["year"]).strip().lower() in merged_era_lookup
                )
            )
        ]

    waiting_for = max(total_members - selected_members, 0)
    return {
        "movies": movies,
        "merged_genres": merged_genres,
        "merged_languages": merged_languages,
        "merged_eras": merged_eras,
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

    if not any(movie["id"] == swipe.movie_id for movie in MOVIES):
        raise HTTPException(status_code=404, detail="Movie not found")

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

                # Get movie details
                movie = next((m for m in MOVIES if m["id"] == swipe.movie_id), None)

                # Notify all room members
                await manager.send_to_room({
                    "type": "match",
                    "movie": movie
                }, room_code)
    
    return {"status": "success"}

@api_router.get("/matches/{room_code}")
async def get_matches(room_code: str):
    matches = await db.matches.find({"room_code": room_code}, {"_id": 0}).to_list(100)
    
    # Enrich with movie details
    for match in matches:
        movie = next((m for m in MOVIES if m["id"] == match["movie_id"]), None)
        match["movie"] = movie
    
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