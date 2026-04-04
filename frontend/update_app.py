import re

with open("frontend/src/App.js", "r") as f:
    content = f.read()

# 1. Add page state
content = re.sub(
    r"const \[movies, setMovies\] = useState\(\[\]\);",
    "const [movies, setMovies] = useState([]);\n  const [page, setPage] = useState(1);",
    content
)

# 2. Update loadRoomMovies
old_loadRoom = """  const loadRoomMovies = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/rooms/${roomCode}/movies`);
      const {
        movies: roomMovies,
        waiting_for,
        selected_members,
        total_members,
      } = response.data;

      setSelectedMembers(selected_members);
      setTotalMembers(total_members);
      setWaitingForMembers(waiting_for > 0);

      if (waiting_for > 0) {
        setMovies([]);
        return false;
      }

      setMovies(roomMovies);

      if (roomMovies.length === 0) {
        toast.error("No movies found for the merged categories");
        return false;
      }

      return true;
    } catch (error) {
      toast.error("Failed to load movies");
      return false;
    }
  }, [roomCode]);"""

new_loadRoom = """  const loadRoomMovies = useCallback(async (pageNum = 1) => {
    try {
      const response = await axios.get(`${API}/rooms/${roomCode}/movies`, {
        params: { page: pageNum }
      });
      const {
        movies: roomMovies,
        waiting_for,
        selected_members,
        total_members,
      } = response.data;

      setSelectedMembers(selected_members);
      setTotalMembers(total_members);
      setWaitingForMembers(waiting_for > 0);

      if (waiting_for > 0) {
        if (pageNum === 1) setMovies([]);
        return false;
      }

      if (pageNum === 1) {
        setMovies(roomMovies);
      } else {
        setMovies(prev => {
          const newMovies = roomMovies.filter(
            newMovie => !prev.some(existingMovie => existingMovie.id === newMovie.id)
          );
          return [...prev, ...newMovies];
        });
      }

      if (roomMovies.length === 0 && pageNum === 1) {
        toast.error("No movies found for the merged categories");
        return false;
      } else if (roomMovies.length === 0 && pageNum > 1) {
        // Optionally handle when no more pages exist
      }

      return true;
    } catch (error) {
      toast.error("Failed to load movies");
      return false;
    }
  }, [roomCode]);"""

content = content.replace(old_loadRoom, new_loadRoom)

# 3. Update handleSwipe
old_handleSwipe = """  const handleSwipe = async (direction) => {
    const movie = movies[currentIndex];

    if (!movie) {
      return;
    }
    
    try {
      await axios.post(`${API}/swipe`, {
        room_code: roomCode,
        user_id: userId,
        movie_id: movie.id,
        direction
      });
      
      if (currentIndex < movies.length - 1) {
        setCurrentIndex(currentIndex + 1);
      } else {
        toast.success("No more movies! Check your matches.");
      }
    } catch (error) {
      toast.error("Failed to record swipe");
    }
  };"""

new_handleSwipe = """  const handleSwipe = async (direction) => {
    const movie = movies[currentIndex];

    if (!movie) {
      return;
    }
    
    try {
      await axios.post(`${API}/swipe`, {
        room_code: roomCode,
        user_id: userId,
        movie_id: movie.id,
        direction
      });
      
      const nextIndex = currentIndex + 1;
      
      if (nextIndex < movies.length) {
        setCurrentIndex(nextIndex);
        // Pre-fetch next page when 3 movies away from the end
        if (nextIndex === movies.length - 3) {
          const nextPage = page + 1;
          setPage(nextPage);
          loadRoomMovies(nextPage);
        }
      } else {
        // End of list reached exactly, fetch next batch and show loader
        const nextPage = page + 1;
        setPage(nextPage);
        setCurrentIndex(nextIndex);
        loadRoomMovies(nextPage);
      }
    } catch (error) {
      toast.error("Failed to record swipe");
    }
  };"""

content = content.replace(old_handleSwipe, new_handleSwipe)

# 4. In startWithSelectedGenres update `loadRoomMovies()` to `loadRoomMovies(1)` and resetting page
old_startWith = """    const loaded = await loadRoomMovies();
    if (loaded) {
      setCurrentIndex(0);
    }"""
new_startWith = """    const loaded = await loadRoomMovies(1);
    if (loaded) {
      setPage(1);
      setCurrentIndex(0);
    }"""
content = content.replace(old_startWith, new_startWith)

with open("frontend/src/App.js", "w") as f:
    f.write(content)

