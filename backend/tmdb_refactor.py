import re
import os

with open("backend/server.py", "r") as f:
    text = f.read()

# Replace the entire MOVIES logic up to get_active_movies with the TMDB Discover logic.
marker_start = "# Mock movie data\nMOVIES = ["
marker_end = "def get_active_movies() -> List[dict]:\n    # Prefer movies with real posters; fallback to full list if enrichment ever under-delivers.\n    return REAL_POSTER_MOVIES if REAL_POSTER_MOVIES else MOVIES"

if marker_start in text and marker_end in text:
    before = text.split(marker_start)[0]
    after = text.split(marker_end)[1]
else:
    print("Could not find markers to replace.")
    exit(1)

tmdb_logic = """# TMDB Configuration
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

async def fetch_tmdb_movies(genres: list[str], languages: list[str], page: int = 1) -> list[dict]:
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
        "include_adult": "false",
        "vote_count.gte": "100" # Only fetch movies with at least 100 votes to ensure quality
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

"""

# Now we need to update the endpoints that relied on the static data:
# 1. get_genres, get_languages, get_eras
# 2. submit_genre_preferences
# 3. get_room_movies
# 4. record_swipe
# 5. get_matches

after = after.replace("""@api_router.get("/genres")
async def get_genres():
    genres = sorted({movie["genre"] for movie in get_active_movies()})
    return genres""", """@api_router.get("/genres")
async def get_genres():
    return sorted(list(TMDB_GENRES.keys()))""")

after = after.replace("""@api_router.get("/eras")
async def get_eras():
    return ["Classic", "2000s", "2010s+"]""", """@api_router.get("/eras")
async def get_eras():
    return SUPPORTED_ERAS""")

after = after.replace("""@api_router.get("/movies")
async def get_movies(genres: Optional[str] = Query(default=None)):
    active_movies = get_active_movies()
    if not genres:
        return active_movies

    genre_filter = {
        genre.strip().lower()
        for genre in genres.split(",")
        if genre.strip()
    }

    if not genre_filter:
        return active_movies

    return [
        movie for movie in active_movies if movie["genre"].strip().lower() in genre_filter
    ]""", """@api_router.get("/movies")
async def get_movies(genres: Optional[str] = Query(default=None)):
    parsed_genres = [g.strip() for g in genres.split(",")] if genres else []
    return await fetch_tmdb_movies(parsed_genres, list(TMDB_LANGUAGES.keys()), page=1)""")

after = after.replace("""    valid_genres = {movie["genre"] for movie in get_active_movies()}""", """    valid_genres = set(TMDB_GENRES.keys())""")


get_room_movies_old = """@api_router.get("/rooms/{room_code}/movies")
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
        movies = get_active_movies()
    else:
        merged_lookup = {genre.lower() for genre in merged_genres}
        merged_language_lookup = {language.lower() for language in merged_languages}
        movies = [
            movie
            for movie in get_active_movies()
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
    }"""

get_room_movies_new = """@api_router.get("/rooms/{room_code}/movies")
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

    # Fetch dynamic batch from TMDB
    movies = await fetch_tmdb_movies(query_genres, query_languages, page=page)

    waiting_for = max(total_members - selected_members, 0)
    return {
        "movies": movies,
        "merged_genres": merged_genres,
        "merged_languages": merged_languages,
        "selected_members": selected_members,
        "total_members": total_members,
        "waiting_for": waiting_for,
    }"""
after = after.replace(get_room_movies_old, get_room_movies_new)

# Update Swipe (Remove validation since we don't have all movies in memory)
after = after.replace("""    if not any(movie["id"] == swipe.movie_id for movie in MOVIES):
        raise HTTPException(status_code=404, detail="Movie not found")""", "")

# Update Match fetch (on Swipe)
after = after.replace("""                # Get movie details
                movie = next((m for m in MOVIES if m["id"] == swipe.movie_id), None)""", """                # Get movie details dynamically
                movie = await fetch_movie_by_id(swipe.movie_id)
                if movie:
                    await db.matches.update_one(
                        {"room_code": room_code, "movie_id": swipe.movie_id},
                        {"$set": {"movie_cache": movie}}
                    )""")

# Update Matches Endpoints
after = after.replace("""@api_router.get("/matches/{room_code}")
async def get_matches(room_code: str):
    matches = await db.matches.find({"room_code": room_code}, {"_id": 0}).to_list(100)
    
    # Enrich with movie details
    for match in matches:
        movie = next((m for m in MOVIES if m["id"] == match["movie_id"]), None)
        match["movie"] = movie
    
    return matches""", """@api_router.get("/matches/{room_code}")
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
            
    return matches""")


updated_code = before + tmdb_logic + after

with open("backend/server.py", "w") as f:
    f.write(updated_code)
print("done")
