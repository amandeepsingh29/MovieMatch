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


ADDITIONAL_MOVIES = [
    {"title": "The Batman", "year": 2022, "genre": "Action", "language": "English"},
    {"title": "Batman Begins", "year": 2005, "genre": "Action", "language": "English"},
    {"title": "The Batman", "year": 1989, "genre": "Action", "language": "English"},
    {"title": "The Avengers", "year": 2012, "genre": "Action", "language": "English"},
    {"title": "Avengers: Endgame", "year": 2019, "genre": "Action", "language": "English"},
    {"title": "John Wick", "year": 2014, "genre": "Action", "language": "English"},
    {"title": "John Wick: Chapter 4", "year": 2023, "genre": "Action", "language": "English"},
    {"title": "The Raid", "year": 2011, "genre": "Action", "language": "Indonesian"},
    {"title": "The Raid 2", "year": 2014, "genre": "Action", "language": "Indonesian"},
    {"title": "Mission: Impossible - Fallout", "year": 2018, "genre": "Action", "language": "English"},
    {"title": "Top Gun: Maverick", "year": 2022, "genre": "Action", "language": "English"},
    {"title": "Casino Royale", "year": 2006, "genre": "Action", "language": "English"},
    {"title": "The Bourne Ultimatum", "year": 2007, "genre": "Action", "language": "English"},
    {"title": "Baby Driver", "year": 2017, "genre": "Action", "language": "English"},
    {"title": "Madras Cafe", "year": 2013, "genre": "Action", "language": "Hindi"},

    {"title": "The Hangover", "year": 2009, "genre": "Comedy", "language": "English"},
    {"title": "Superbad", "year": 2007, "genre": "Comedy", "language": "English"},
    {"title": "Crazy Rich Asians", "year": 2018, "genre": "Comedy", "language": "English"},
    {"title": "Palm Springs", "year": 2020, "genre": "Comedy", "language": "English"},
    {"title": "Jojo Rabbit", "year": 2019, "genre": "Comedy", "language": "English"},
    {"title": "The Grand Budapest Hotel", "year": 2014, "genre": "Comedy", "language": "English"},
    {"title": "Knives Out", "year": 2019, "genre": "Comedy", "language": "English"},
    {"title": "Glass Onion", "year": 2022, "genre": "Comedy", "language": "English"},
    {"title": "Queen", "year": 2014, "genre": "Comedy", "language": "Hindi"},
    {"title": "Bhool Bhulaiyaa", "year": 2007, "genre": "Comedy", "language": "Hindi"},
    {"title": "Lage Raho Munna Bhai", "year": 2006, "genre": "Comedy", "language": "Hindi"},
    {"title": "Carry On Jatta 2", "year": 2018, "genre": "Comedy", "language": "Punjabi"},
    {"title": "Kala Shah Kala", "year": 2019, "genre": "Comedy", "language": "Punjabi"},

    {"title": "Se7en", "year": 1995, "genre": "Crime", "language": "English"},
    {"title": "Prisoners", "year": 2013, "genre": "Crime", "language": "English"},
    {"title": "Gone Baby Gone", "year": 2007, "genre": "Crime", "language": "English"},
    {"title": "The Departed", "year": 2006, "genre": "Crime", "language": "English"},
    {"title": "Zodiac", "year": 2007, "genre": "Crime", "language": "English"},
    {"title": "No Country for Old Men", "year": 2007, "genre": "Crime", "language": "English"},
    {"title": "Heat", "year": 1995, "genre": "Crime", "language": "English"},
    {"title": "The Irishman", "year": 2019, "genre": "Crime", "language": "English"},
    {"title": "Vikram Vedha", "year": 2017, "genre": "Crime", "language": "Tamil"},
    {"title": "Drishyam", "year": 2015, "genre": "Crime", "language": "Hindi"},
    {"title": "Talvar", "year": 2015, "genre": "Crime", "language": "Hindi"},

    {"title": "The Green Mile", "year": 1999, "genre": "Drama", "language": "English"},
    {"title": "Good Will Hunting", "year": 1997, "genre": "Drama", "language": "English"},
    {"title": "The Pursuit of Happyness", "year": 2006, "genre": "Drama", "language": "English"},
    {"title": "The Pianist", "year": 2002, "genre": "Drama", "language": "English"},
    {"title": "A Beautiful Mind", "year": 2001, "genre": "Drama", "language": "English"},
    {"title": "Manchester by the Sea", "year": 2016, "genre": "Drama", "language": "English"},
    {"title": "The Whale", "year": 2022, "genre": "Drama", "language": "English"},
    {"title": "Taare Zameen Par", "year": 2007, "genre": "Drama", "language": "Hindi"},
    {"title": "Udaan", "year": 2010, "genre": "Drama", "language": "Hindi"},
    {"title": "Airlift", "year": 2016, "genre": "Drama", "language": "Hindi"},
    {"title": "Qismat", "year": 2018, "genre": "Drama", "language": "Punjabi"},
    {"title": "Chhichhore", "year": 2019, "genre": "Drama", "language": "Hindi"},

    {"title": "The Hobbit: An Unexpected Journey", "year": 2012, "genre": "Adventure", "language": "English"},
    {"title": "The Hobbit: The Desolation of Smaug", "year": 2013, "genre": "Adventure", "language": "English"},
    {"title": "The Hobbit: The Battle of the Five Armies", "year": 2014, "genre": "Adventure", "language": "English"},
    {"title": "Pirates of the Caribbean: The Curse of the Black Pearl", "year": 2003, "genre": "Adventure", "language": "English"},
    {"title": "Life of Pi", "year": 2012, "genre": "Adventure", "language": "English"},
    {"title": "Jumanji: Welcome to the Jungle", "year": 2017, "genre": "Adventure", "language": "English"},
    {"title": "Dune", "year": 2021, "genre": "Adventure", "language": "English"},
    {"title": "Dune: Part Two", "year": 2024, "genre": "Adventure", "language": "English"},

    {"title": "The Lion King", "year": 1994, "genre": "Animation", "language": "English"},
    {"title": "Toy Story", "year": 1995, "genre": "Animation", "language": "English"},
    {"title": "Toy Story 3", "year": 2010, "genre": "Animation", "language": "English"},
    {"title": "Inside Out", "year": 2015, "genre": "Animation", "language": "English"},
    {"title": "Soul", "year": 2020, "genre": "Animation", "language": "English"},
    {"title": "Klaus", "year": 2019, "genre": "Animation", "language": "English"},
    {"title": "How to Train Your Dragon", "year": 2010, "genre": "Animation", "language": "English"},
    {"title": "Howl's Moving Castle", "year": 2004, "genre": "Animation", "language": "Japanese"},
    {"title": "Ponyo", "year": 2008, "genre": "Animation", "language": "Japanese"},

    {"title": "Blade Runner", "year": 1982, "genre": "Sci-Fi", "language": "English"},
    {"title": "The Martian", "year": 2015, "genre": "Sci-Fi", "language": "English"},
    {"title": "Ex Machina", "year": 2014, "genre": "Sci-Fi", "language": "English"},
    {"title": "Her", "year": 2013, "genre": "Sci-Fi", "language": "English"},
    {"title": "Edge of Tomorrow", "year": 2014, "genre": "Sci-Fi", "language": "English"},
    {"title": "District 9", "year": 2009, "genre": "Sci-Fi", "language": "English"},
    {"title": "Looper", "year": 2012, "genre": "Sci-Fi", "language": "English"},
    {"title": "Donnie Darko", "year": 2001, "genre": "Sci-Fi", "language": "English"},

    {"title": "Get Out", "year": 2017, "genre": "Thriller", "language": "English"},
    {"title": "A Quiet Place", "year": 2018, "genre": "Thriller", "language": "English"},
    {"title": "A Quiet Place Part II", "year": 2020, "genre": "Thriller", "language": "English"},
    {"title": "The Invisible Man", "year": 2020, "genre": "Thriller", "language": "English"},
    {"title": "Sicario", "year": 2015, "genre": "Thriller", "language": "English"},
    {"title": "Nightcrawler", "year": 2014, "genre": "Thriller", "language": "English"},
    {"title": "Black Swan", "year": 2010, "genre": "Thriller", "language": "English"},
    {"title": "The Wailing", "year": 2016, "genre": "Thriller", "language": "Korean"},
    {"title": "I Saw the Devil", "year": 2010, "genre": "Thriller", "language": "Korean"},
    {"title": "Ratsasan", "year": 2018, "genre": "Thriller", "language": "Tamil"},

    {"title": "The Notebook", "year": 2004, "genre": "Romance", "language": "English"},
    {"title": "Before Sunrise", "year": 1995, "genre": "Romance", "language": "English"},
    {"title": "Before Sunset", "year": 2004, "genre": "Romance", "language": "English"},
    {"title": "La La Land", "year": 2016, "genre": "Romance", "language": "English"},
    {"title": "Pride & Prejudice", "year": 2005, "genre": "Romance", "language": "English"},
    {"title": "About Time", "year": 2013, "genre": "Romance", "language": "English"},
    {"title": "Jab We Met", "year": 2007, "genre": "Romance", "language": "Hindi"},
    {"title": "Barfi!", "year": 2012, "genre": "Romance", "language": "Hindi"},
    {"title": "Rockstar", "year": 2011, "genre": "Romance", "language": "Hindi"},

    {"title": "The Shape of Water", "year": 2017, "genre": "Fantasy", "language": "English"},
    {"title": "Doctor Strange", "year": 2016, "genre": "Fantasy", "language": "English"},
    {"title": "Harry Potter and the Prisoner of Azkaban", "year": 2004, "genre": "Fantasy", "language": "English"},
    {"title": "Harry Potter and the Goblet of Fire", "year": 2005, "genre": "Fantasy", "language": "English"},
    {"title": "Harry Potter and the Deathly Hallows: Part 1", "year": 2010, "genre": "Fantasy", "language": "English"},
    {"title": "Harry Potter and the Deathly Hallows: Part 2", "year": 2011, "genre": "Fantasy", "language": "English"},
    {"title": "Stardust", "year": 2007, "genre": "Fantasy", "language": "English"},

    {"title": "Logan", "year": 2017, "genre": "Action", "language": "English"},
    {"title": "Skyfall", "year": 2012, "genre": "Action", "language": "English"},
    {"title": "The Equalizer", "year": 2014, "genre": "Action", "language": "English"},
    {"title": "Rangasthalam", "year": 2018, "genre": "Action", "language": "Telugu"},

    {"title": "Booksmart", "year": 2019, "genre": "Comedy", "language": "English"},
    {"title": "The Nice Guys", "year": 2016, "genre": "Comedy", "language": "English"},
    {"title": "Fukrey", "year": 2013, "genre": "Comedy", "language": "Hindi"},
    {"title": "Shadaa", "year": 2019, "genre": "Comedy", "language": "Punjabi"},

    {"title": "Mystic River", "year": 2003, "genre": "Crime", "language": "English"},
    {"title": "The Town", "year": 2010, "genre": "Crime", "language": "English"},
    {"title": "Kaithi", "year": 2019, "genre": "Crime", "language": "Tamil"},
    {"title": "Paatal Lok", "year": 2020, "genre": "Crime", "language": "Hindi"},

    {"title": "12 Years a Slave", "year": 2013, "genre": "Drama", "language": "English"},
    {"title": "The King's Speech", "year": 2010, "genre": "Drama", "language": "English"},
    {"title": "Neerja", "year": 2016, "genre": "Drama", "language": "Hindi"},
    {"title": "Sardar Udham", "year": 2021, "genre": "Drama", "language": "Hindi"},

    {"title": "King Kong", "year": 2005, "genre": "Adventure", "language": "English"},
    {"title": "Avatar", "year": 2009, "genre": "Adventure", "language": "English"},
    {"title": "Avatar: The Way of Water", "year": 2022, "genre": "Adventure", "language": "English"},

    {"title": "Moana", "year": 2016, "genre": "Animation", "language": "English"},
    {"title": "Frozen", "year": 2013, "genre": "Animation", "language": "English"},
    {"title": "The Wind Rises", "year": 2013, "genre": "Animation", "language": "Japanese"},

    {"title": "Children of Men", "year": 2006, "genre": "Sci-Fi", "language": "English"},
    {"title": "Moon", "year": 2009, "genre": "Sci-Fi", "language": "English"},
    {"title": "Source Code", "year": 2011, "genre": "Sci-Fi", "language": "English"},

    {"title": "The Conjuring", "year": 2013, "genre": "Thriller", "language": "English"},
    {"title": "Shaitaan", "year": 2024, "genre": "Thriller", "language": "Hindi"},
    {"title": "Maharaja", "year": 2024, "genre": "Thriller", "language": "Tamil"},

    {"title": "Veer-Zaara", "year": 2004, "genre": "Romance", "language": "Hindi"},
    {"title": "A Star Is Born", "year": 2018, "genre": "Romance", "language": "English"},
    {"title": "96", "year": 2018, "genre": "Romance", "language": "Tamil"},

    {"title": "Fantastic Beasts and Where to Find Them", "year": 2016, "genre": "Fantasy", "language": "English"},
    {"title": "Miss Peregrine's Home for Peculiar Children", "year": 2016, "genre": "Fantasy", "language": "English"},
]


def expand_movies_with_real_catalog(movies: List[dict], additional_movies: List[dict]) -> List[dict]:
    expanded = list(movies)
    next_id = max(int(movie["id"]) for movie in movies) + 1
    seen = {
        (movie["title"].strip().lower(), movie["year"], movie["language"].strip().lower())
        for movie in movies
    }

    for movie in additional_movies:
        key = (movie["title"].strip().lower(), movie["year"], movie["language"].strip().lower())
        if key in seen:
            continue

        expanded.append({
            "id": str(next_id),
            "title": movie["title"],
            "year": movie["year"],
            "genre": movie["genre"],
            "language": movie["language"],
            "poster": movie.get("poster", ""),
            "trailer": movie.get("trailer", ""),
        })
        seen.add(key)
        next_id += 1

    return expanded


MOVIES = expand_movies_with_real_catalog(MOVIES, ADDITIONAL_MOVIES)


def build_poster_fallback(title: str) -> str:
    return f"https://placehold.co/600x900/101010/ffffff/png?text={quote_plus(title)}"


def is_reachable_image(url: str) -> bool:
    if not url:
        return False

    try:
        req = Request(url, method="HEAD")
        with urlopen(req, timeout=4) as response:
            status = getattr(response, "status", 200)
            return 200 <= status < 400
    except Exception:
        try:
            req = Request(url, method="GET")
            with urlopen(req, timeout=4) as response:
                status = getattr(response, "status", 200)
                return 200 <= status < 400
        except Exception:
            return False


def fetch_itunes_poster(title: str, year: int) -> str:
    query = urlencode({
        "term": title,
        "media": "movie",
        "entity": "movie",
        "limit": 10,
    })
    endpoint = f"https://itunes.apple.com/search?{query}"

    try:
        req = Request(endpoint, headers={"User-Agent": "MovieMatch/1.0"})
        with urlopen(req, timeout=6) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return ""

    candidates = payload.get("results", [])
    best_url = ""
    best_score = 10**9

    for item in candidates:
        artwork = item.get("artworkUrl100")
        release_date = item.get("releaseDate", "")
        if not artwork:
            continue

        release_year = 0
        if len(release_date) >= 4 and release_date[:4].isdigit():
            release_year = int(release_date[:4])

        score = abs(release_year - year) if release_year else 100
        if score < best_score:
            best_score = score
            best_url = artwork.replace("100x100bb", "1000x1000bb")

    return best_url


def enrich_posters(movies: List[dict]) -> None:
    resolved: dict[tuple[str, int], str] = {}

    for movie in movies:
        title = movie["title"]
        year = movie["year"]
        existing = (movie.get("poster") or "").strip()

        # Trust curated URLs to avoid expensive startup-time network checks.
        if existing:
            resolved[(title, year)] = existing
            continue

        cached = resolved.get((title, year), "")
        if cached:
            movie["poster"] = cached
            continue

        fetched = fetch_itunes_poster(title, year)
        if fetched and is_reachable_image(fetched):
            movie["poster"] = fetched
            resolved[(title, year)] = fetched


enrich_posters(MOVIES)


# Ensure every movie has stable fallback assets.
for movie in MOVIES:
    movie["poster_fallback"] = build_poster_fallback(movie["title"])
    if not movie.get("poster"):
        movie["poster"] = movie["poster_fallback"]
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
    genres = sorted({movie["genre"] for movie in MOVIES})
    return genres


@api_router.get("/languages")
async def get_languages():
    return SUPPORTED_LANGUAGES


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

    if not cleaned_genres:
        raise HTTPException(status_code=400, detail="Select at least one genre")
    if not cleaned_languages:
        raise HTTPException(status_code=400, detail="Select at least one language")

    valid_genres = {movie["genre"] for movie in MOVIES}
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

    if not merged_genres and not merged_languages:
        movies = MOVIES
    else:
        merged_lookup = {genre.lower() for genre in merged_genres}
        merged_language_lookup = {language.lower() for language in merged_languages}
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
            )
        ]

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