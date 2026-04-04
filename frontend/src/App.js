import { useState, useEffect, useCallback, useRef } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route, useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import { motion, useMotionValue, useTransform, AnimatePresence } from "framer-motion";
import { Film, Users, Copy, Check } from "lucide-react";
import { Toaster, toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://localhost:8000";
const API = `${BACKEND_URL}/api`;
const WS_URL = BACKEND_URL.replace('https://', 'wss://').replace('http://', 'ws://') + '/api';

const Landing = () => {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [roomCode, setRoomCode] = useState("");
  const [mode, setMode] = useState(null);

  const handleCreateRoom = async () => {
    if (!username.trim()) {
      toast.error("Please enter your name");
      return;
    }

    try {
      const response = await axios.post(`${API}/rooms/create`, { username });
      const { room_code, user_id } = response.data;
      localStorage.setItem('user_id', user_id);
      localStorage.setItem('username', username);
      navigate(`/room/${room_code}`);
    } catch (error) {
      toast.error("Failed to create room");
    }
  };

  const handleJoinRoom = async () => {
    if (!username.trim() || !roomCode.trim()) {
      toast.error("Please enter your name and room code");
      return;
    }

    try {
      const response = await axios.post(`${API}/rooms/join`, { 
        username, 
        room_code: roomCode.toUpperCase() 
      });
      const { user_id } = response.data;
      localStorage.setItem('user_id', user_id);
      localStorage.setItem('username', username);
      navigate(`/room/${roomCode.toUpperCase()}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to join room");
    }
  };

  return (
    <div className="min-h-screen bg-cinema-black film-grain flex items-center justify-center p-4">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center space-y-4">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", bounce: 0.5 }}
          >
            <Film className="w-20 h-20 text-cinema-red mx-auto" style={{ filter: 'drop-shadow(0 0 20px rgba(229, 9, 20, 0.5))' }} />
          </motion.div>
          <h1 className="font-secondary text-6xl text-white tracking-wide uppercase" data-testid="app-title">MovieMatch</h1>
          <p className="text-cinema-gold font-bold uppercase text-sm tracking-widest" data-testid="app-tagline">Swipe Together, Watch Together</p>
        </div>

        {!mode && (
          <motion.div 
            className="space-y-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <button
              onClick={() => setMode('create')}
              className="w-full bg-cinema-red text-white rounded-full py-4 font-bold uppercase tracking-widest hover:bg-red-700 transition-colors shadow-[0_0_15px_rgba(229,9,20,0.5)]"
              data-testid="create-room-btn"
            >
              Create New Room
            </button>
            <button
              onClick={() => setMode('join')}
              className="w-full bg-transparent border border-white/20 text-white rounded-full py-4 font-bold uppercase tracking-widest hover:bg-white/10 transition-colors"
              data-testid="join-room-btn"
            >
              Join Existing Room
            </button>
          </motion.div>
        )}

        {mode === 'create' && (
          <motion.div 
            className="space-y-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <input
              type="text"
              placeholder="Enter your name"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-white/5 border border-white/10 text-white placeholder:text-white/30 rounded-lg px-4 h-12 focus:ring-2 focus:ring-cinema-red focus:border-transparent outline-none"
              data-testid="username-input"
            />
            <button
              onClick={handleCreateRoom}
              className="w-full bg-cinema-red text-white rounded-full py-4 font-bold uppercase tracking-widest hover:bg-red-700 transition-colors shadow-[0_0_15px_rgba(229,9,20,0.5)]"
              data-testid="submit-create-room"
            >
              Create Room
            </button>
            <button
              onClick={() => setMode(null)}
              className="w-full text-white/50 hover:text-white transition-colors text-sm"
              data-testid="back-btn"
            >
              Back
            </button>
          </motion.div>
        )}

        {mode === 'join' && (
          <motion.div 
            className="space-y-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <input
              type="text"
              placeholder="Enter your name"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-white/5 border border-white/10 text-white placeholder:text-white/30 rounded-lg px-4 h-12 focus:ring-2 focus:ring-cinema-red focus:border-transparent outline-none"
              data-testid="username-input-join"
            />
            <input
              type="text"
              placeholder="Enter room code"
              value={roomCode}
              onChange={(e) => setRoomCode(e.target.value.toUpperCase())}
              className="w-full bg-white/5 border border-white/10 text-white placeholder:text-white/30 rounded-lg px-4 h-12 focus:ring-2 focus:ring-cinema-red focus:border-transparent outline-none uppercase"
              data-testid="room-code-input"
            />
            <button
              onClick={handleJoinRoom}
              className="w-full bg-cinema-red text-white rounded-full py-4 font-bold uppercase tracking-widest hover:bg-red-700 transition-colors shadow-[0_0_15px_rgba(229,9,20,0.5)]"
              data-testid="submit-join-room"
            >
              Join Room
            </button>
            <button
              onClick={() => setMode(null)}
              className="w-full text-white/50 hover:text-white transition-colors text-sm"
              data-testid="back-btn-join"
            >
              Back
            </button>
          </motion.div>
        )}
      </div>
    </div>
  );
};

const Room = () => {
  const { roomCode } = useParams();
  const navigate = useNavigate();
  const [room, setRoom] = useState(null);
  const [copied, setCopied] = useState(false);
  const userId = localStorage.getItem('user_id');
  const wsErrorShownRef = useRef(false);
  const wsReconnectAttemptsRef = useRef(0);
  const wsReconnectTimerRef = useRef(null);
  const wsRef = useRef(null);

  const loadRoom = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/rooms/${roomCode}`);
      setRoom(response.data);
    } catch (error) {
      if (error.response?.status === 404) {
        toast.error("Room not found");
        navigate('/');
        return;
      }

      toast.error("Connection lost. Reconnecting...");
    }
  }, [navigate, roomCode]);

  useEffect(() => {
    if (!userId) {
      navigate('/');
      return;
    }

    loadRoom();
    let intentionalClose = false;

    const connectWebSocket = () => {
      const ws = new WebSocket(`${WS_URL}/ws/${roomCode}`);
      wsRef.current = ws;

      ws.onopen = () => {
        wsReconnectAttemptsRef.current = 0;
        wsErrorShownRef.current = false;
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'member_joined') {
          loadRoom();
          toast.success(`${data.username} joined the room!`);
        } else if (data.type === 'room_started') {
          navigate(`/swipe/${roomCode}`);
        }
      };

      ws.onerror = () => {
        // Browser onerror is intentionally generic; rely on onclose for actionable UX.
      };

      ws.onclose = (event) => {
        if (intentionalClose) {
          return;
        }

        if (!event.wasClean && !wsErrorShownRef.current) {
          wsErrorShownRef.current = true;
          toast.error("Live connection lost. Reconnecting...");
        }

        const attempts = wsReconnectAttemptsRef.current;
        const delayMs = Math.min(1000 * Math.pow(2, attempts), 5000);
        wsReconnectAttemptsRef.current += 1;

        wsReconnectTimerRef.current = setTimeout(() => {
          if (!intentionalClose) {
            connectWebSocket();
            loadRoom();
          }
        }, delayMs);
      };
    };

    connectWebSocket();

    const handleVisibilityOrFocus = () => {
      if (document.visibilityState === 'visible') {
        loadRoom();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityOrFocus);
    window.addEventListener('focus', handleVisibilityOrFocus);

    return () => {
      intentionalClose = true;
      if (wsReconnectTimerRef.current) {
        clearTimeout(wsReconnectTimerRef.current);
      }
      document.removeEventListener('visibilitychange', handleVisibilityOrFocus);
      window.removeEventListener('focus', handleVisibilityOrFocus);
      wsRef.current?.close();
    };
  }, [loadRoom, navigate, roomCode, userId]);

  const copyRoomCode = async () => {
    try {
      await navigator.clipboard.writeText(roomCode);
      setCopied(true);
      toast.success("Room code copied!");
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      // Fallback for clipboard permissions
      toast.success(`Room code: ${roomCode}`);
    }
  };

  const startSwiping = async () => {
    try {
      await axios.post(`${API}/rooms/start`, { room_code: roomCode });
    } catch (error) {
      toast.error("Failed to start");
    }
  };

  if (!room) {
    return (
      <div className="min-h-screen bg-cinema-black film-grain flex items-center justify-center p-4">
        <div className="text-center space-y-3">
          <h2 className="font-secondary text-3xl text-white tracking-wide uppercase" data-testid="room-loading-title">Reconnecting Room...</h2>
          <p className="text-white/60 text-sm" data-testid="room-loading-subtitle">Please wait while we restore your room session.</p>
        </div>
      </div>
    );
  }

  const isCreator = room.members[0]?.user_id === userId;

  return (
    <div className="min-h-screen bg-cinema-black film-grain flex items-center justify-center p-4">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center space-y-4">
          <Film className="w-16 h-16 text-cinema-red mx-auto" style={{ filter: 'drop-shadow(0 0 20px rgba(229, 9, 20, 0.5))' }} />
          <h2 className="font-secondary text-4xl text-white tracking-wide uppercase" data-testid="waiting-room-title">Waiting Room</h2>
        </div>

        <div className="backdrop-blur-xl bg-black/60 border border-white/10 rounded-xl p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white/50 text-sm uppercase tracking-wider">Room Code</p>
              <p className="text-white text-3xl font-secondary tracking-wider" data-testid="room-code-display">{roomCode}</p>
            </div>
            <button
              onClick={copyRoomCode}
              className="p-3 bg-white/5 hover:bg-white/10 rounded-lg transition-colors"
              data-testid="copy-code-btn"
            >
              {copied ? <Check className="w-5 h-5 text-cinema-gold" /> : <Copy className="w-5 h-5 text-white" />}
            </button>
          </div>

          <div>
            <div className="flex items-center gap-2 mb-3">
              <Users className="w-5 h-5 text-cinema-gold" />
              <p className="text-white/50 text-sm uppercase tracking-wider">Members ({room.members.length})</p>
            </div>
            <div className="space-y-2">
              {room.members.map((member, idx) => (
                <div key={idx} className="bg-white/5 rounded-lg p-3 flex items-center gap-3" data-testid={`member-${idx}`}>
                  <div className="w-10 h-10 bg-cinema-red rounded-full flex items-center justify-center text-white font-bold">
                    {member.username[0].toUpperCase()}
                  </div>
                  <div>
                    <p className="text-white font-medium">{member.username}</p>
                    {idx === 0 && <p className="text-cinema-gold text-xs uppercase">Host</p>}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {isCreator && (
            <button
              onClick={startSwiping}
              disabled={room.members.length < 2}
              className="w-full bg-cinema-red text-white rounded-full py-4 font-bold uppercase tracking-widest hover:bg-red-700 transition-colors shadow-[0_0_15px_rgba(229,9,20,0.5)] disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="start-swiping-btn"
            >
              Start Swiping
            </button>
          )}

          {!isCreator && (
            <p className="text-center text-white/50 text-sm" data-testid="waiting-message">Waiting for host to start...</p>
          )}
        </div>
      </div>
    </div>
  );
};

const MovieCard = ({ movie, onSwipe }) => {
  const x = useMotionValue(0);
  const rotate = useTransform(x, [-200, 200], [-20, 20]);
  const opacity = useTransform(x, [-200, -100, 0, 100, 200], [0, 1, 1, 1, 0]);
  const [posterFailed, setPosterFailed] = useState(false);
  const [usingFallbackPoster, setUsingFallbackPoster] = useState(false);

  const handleDragEnd = (event, info) => {
    if (info.offset.x > 100) {
      onSwipe('like');
    } else if (info.offset.x < -100) {
      onSwipe('dislike');
    }
  };

  return (
    <motion.div
      className="absolute w-full h-full"
      style={{ x, rotate, opacity }}
      drag="x"
      dragConstraints={{ left: 0, right: 0 }}
      onDragEnd={handleDragEnd}
      whileTap={{ scale: 0.95 }}
    >
      <div className="relative w-full h-full rounded-xl overflow-hidden" style={{ boxShadow: '0 0 40px rgba(229, 9, 20, 0.4)' }} data-testid="movie-card">
        {!posterFailed ? (
          <img
            src={usingFallbackPoster ? movie.poster_fallback : movie.poster}
            alt={movie.title}
            className="w-full h-full object-cover"
            onError={() => {
              if (!usingFallbackPoster && movie.poster_fallback) {
                setUsingFallbackPoster(true);
                return;
              }
              setPosterFailed(true);
            }}
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-b from-zinc-800 to-zinc-950 flex items-center justify-center p-6">
            <div className="text-center space-y-3">
              <Film className="w-12 h-12 text-cinema-red mx-auto" />
              <p className="text-white font-secondary text-2xl tracking-wide uppercase">{movie.title}</p>
              <p className="text-white/60 text-sm uppercase tracking-widest">Poster unavailable</p>
            </div>
          </div>
        )}
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black via-black/80 to-transparent p-6 space-y-2">
          <h3 className="font-secondary text-3xl text-white tracking-wide uppercase" data-testid="movie-title">{movie.title}</h3>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-cinema-gold font-bold" data-testid="movie-year">{movie.year}</span>
            <span className="text-white/50">•</span>
            <span className="text-white/70" data-testid="movie-genre">{movie.genre}</span>
          </div>
        </div>
        
        {(movie.trailer_url || movie.imdb_url) && (
          <div className="absolute top-4 right-4 flex flex-col gap-2 items-end">
            {movie.trailer_url && (
              <a
                href={movie.trailer_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 rounded-full px-3 py-2 bg-black/70 border border-white/20 text-white text-xs uppercase tracking-wide hover:bg-black/85 transition-colors"
                data-testid="movie-trailer-link"
              >
                Trailer
              </a>
            )}

            {movie.imdb_url && (
              <a
                href={movie.imdb_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 rounded-full px-3 py-2 bg-black/70 border border-white/20 text-white text-xs uppercase tracking-wide hover:bg-black/85 transition-colors"
                data-testid="movie-imdb-link"
              >
                IMDb
              </a>
            )}

            {movie.imdb_poster_url && (
              <a
                href={movie.imdb_poster_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 rounded-full px-3 py-2 bg-black/70 border border-white/20 text-white text-xs uppercase tracking-wide hover:bg-black/85 transition-colors"
                data-testid="movie-imdb-poster-link"
              >
                IMDb Poster
              </a>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
};

const Swipe = () => {
  const { roomCode } = useParams();
  const navigate = useNavigate();
  const [movies, setMovies] = useState([]);
  const [availableGenres, setAvailableGenres] = useState([]);
  const [availableLanguages, setAvailableLanguages] = useState([]);
  const [availableEras, setAvailableEras] = useState([]);
  const [selectedGenres, setSelectedGenres] = useState([]);
  const [selectedLanguages, setSelectedLanguages] = useState([]);
  const [selectedEras, setSelectedEras] = useState([]);
  const [showGenrePicker, setShowGenrePicker] = useState(true);
  const [waitingForMembers, setWaitingForMembers] = useState(false);
  const [selectedMembers, setSelectedMembers] = useState(0);
  const [totalMembers, setTotalMembers] = useState(0);
  const [selectionSubmitted, setSelectionSubmitted] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showMatch, setShowMatch] = useState(false);
  const [matchedMovie, setMatchedMovie] = useState(null);
  const [userId, setUserId] = useState(localStorage.getItem('user_id'));
  const wsErrorShownRef = useRef(false);
  const wsReconnectAttemptsRef = useRef(0);
  const wsReconnectTimerRef = useRef(null);
  const wsRef = useRef(null);

  const loadGenres = useCallback(async () => {
    try {
      const [genreResponse, languageResponse, eraResponse] = await Promise.all([
        axios.get(`${API}/genres`),
        axios.get(`${API}/languages`),
        axios.get(`${API}/eras`),
      ]);
      setAvailableGenres(genreResponse.data);
      setAvailableLanguages(languageResponse.data);
      setAvailableEras(eraResponse.data);
    } catch (error) {
      toast.error("Failed to load preference options");
    }
  }, []);

  const loadRoomMovies = useCallback(async () => {
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
  }, [roomCode]);

  const toggleGenre = (genre) => {
    setSelectedGenres((prev) => {
      if (prev.includes(genre)) {
        return prev.filter((item) => item !== genre);
      }
      return [...prev, genre];
    });
  };

  const toggleLanguage = (language) => {
    setSelectedLanguages((prev) => {
      if (prev.includes(language)) {
        return prev.filter((item) => item !== language);
      }
      return [...prev, language];
    });
  };

  const toggleEra = (era) => {
    setSelectedEras((prev) => {
      if (prev.includes(era)) {
        return prev.filter((item) => item !== era);
      }
      return [...prev, era];
    });
  };

  const startWithSelectedGenres = async () => {
    if (selectedGenres.length === 0) {
      toast.error("Select at least one category");
      return;
    }

    if (selectedLanguages.length === 0) {
      toast.error("Select at least one language");
      return;
    }

    if (selectedEras.length === 0) {
      toast.error("Select at least one release era");
      return;
    }

    try {
      await axios.post(`${API}/rooms/preferences`, {
        room_code: roomCode,
        user_id: userId,
        genres: selectedGenres,
        languages: selectedLanguages,
        eras: selectedEras,
      });
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to save categories");
      return;
    }

    setSelectionSubmitted(true);
    setShowGenrePicker(false);

    const loaded = await loadRoomMovies();
    if (loaded) {
      setCurrentIndex(0);
    }
  };

  useEffect(() => {
    // Give a moment for localStorage to be available
    const storedUserId = localStorage.getItem('user_id');
    if (storedUserId) {
      setUserId(storedUserId);
    } else {
      // If still no userId after checking, redirect
      setTimeout(() => {
        if (!localStorage.getItem('user_id')) {
          navigate('/');
        }
      }, 500);
      return;
    }

    loadGenres();
    let intentionalClose = false;

    const connectWebSocket = () => {
      const ws = new WebSocket(`${WS_URL}/ws/${roomCode}`);
      wsRef.current = ws;

      ws.onopen = () => {
        wsReconnectAttemptsRef.current = 0;
        wsErrorShownRef.current = false;
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'match') {
          setMatchedMovie(data.movie);
          setShowMatch(true);
        } else if (data.type === 'preferences_updated' && selectionSubmitted) {
          loadRoomMovies();
        }
      };

      ws.onerror = () => {
        // Browser onerror is intentionally generic; rely on onclose for actionable UX.
      };

      ws.onclose = (event) => {
        if (intentionalClose) {
          return;
        }

        if (!event.wasClean && !wsErrorShownRef.current) {
          wsErrorShownRef.current = true;
          toast.error("Live updates disconnected. Reconnecting...");
        }

        const attempts = wsReconnectAttemptsRef.current;
        const delayMs = Math.min(1000 * Math.pow(2, attempts), 5000);
        wsReconnectAttemptsRef.current += 1;

        wsReconnectTimerRef.current = setTimeout(() => {
          if (!intentionalClose) {
            connectWebSocket();
            if (selectionSubmitted) {
              loadRoomMovies();
            }
          }
        }, delayMs);
      };
    };

    connectWebSocket();

    const handleVisibilityOrFocus = () => {
      if (document.visibilityState === 'visible' && selectionSubmitted) {
        loadRoomMovies();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityOrFocus);
    window.addEventListener('focus', handleVisibilityOrFocus);

    return () => {
      intentionalClose = true;
      if (wsReconnectTimerRef.current) {
        clearTimeout(wsReconnectTimerRef.current);
      }
      document.removeEventListener('visibilitychange', handleVisibilityOrFocus);
      window.removeEventListener('focus', handleVisibilityOrFocus);
      wsRef.current?.close();
    };
  }, [loadGenres, loadRoomMovies, navigate, roomCode, selectionSubmitted]);

  useEffect(() => {
    if (!selectionSubmitted || !waitingForMembers) {
      return;
    }

    const timer = setInterval(() => {
      loadRoomMovies();
    }, 2000);

    return () => clearInterval(timer);
  }, [loadRoomMovies, selectionSubmitted, waitingForMembers]);

  const handleSwipe = async (direction) => {
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
  };

  if (showGenrePicker) {
    return (
      <div className="min-h-screen bg-cinema-black film-grain flex items-center justify-center p-4">
        <div className="max-w-md w-full backdrop-blur-xl bg-black/60 border border-white/10 rounded-xl p-6 space-y-6">
          <div className="text-center space-y-3">
            <Film className="w-12 h-12 text-cinema-red mx-auto" style={{ filter: 'drop-shadow(0 0 20px rgba(229, 9, 20, 0.5))' }} />
            <h2 className="font-secondary text-3xl text-white tracking-wide uppercase" data-testid="genre-selection-title">Pick Your Categories</h2>
            <p className="text-white/60 text-sm" data-testid="genre-selection-subtitle">Choose genre, language, and release era before swiping.</p>
          </div>

          <div className="space-y-3">
            <p className="text-white/70 text-xs uppercase tracking-wider" data-testid="question-genres">1. Which genres do you like?</p>
            <div className="grid grid-cols-2 gap-3">
            {availableGenres.map((genre) => {
              const isSelected = selectedGenres.includes(genre);
              return (
                <button
                  key={genre}
                  onClick={() => toggleGenre(genre)}
                  className={`rounded-lg px-3 py-2 text-sm font-bold uppercase tracking-wide transition-colors ${
                    isSelected
                      ? 'bg-cinema-red text-white shadow-[0_0_15px_rgba(229,9,20,0.5)]'
                      : 'bg-white/5 text-white/80 border border-white/10 hover:bg-white/10'
                  }`}
                  data-testid={`genre-option-${genre.toLowerCase()}`}
                >
                  {genre}
                </button>
              );
            })}
            </div>
          </div>

          <div className="space-y-3">
            <p className="text-white/70 text-xs uppercase tracking-wider" data-testid="question-languages">2. Preferred language?</p>
            <div className="grid grid-cols-2 gap-3">
              {availableLanguages.map((language) => {
                const isSelected = selectedLanguages.includes(language);
                return (
                  <button
                    key={language}
                    onClick={() => toggleLanguage(language)}
                    className={`rounded-lg px-3 py-2 text-sm font-bold uppercase tracking-wide transition-colors ${
                      isSelected
                        ? 'bg-cinema-red text-white shadow-[0_0_15px_rgba(229,9,20,0.5)]'
                        : 'bg-white/5 text-white/80 border border-white/10 hover:bg-white/10'
                    }`}
                    data-testid={`language-option-${language.toLowerCase()}`}
                  >
                    {language}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="space-y-3">
            <p className="text-white/70 text-xs uppercase tracking-wider" data-testid="question-era">3. Which release era?</p>
            <div className="grid grid-cols-3 gap-3">
              {availableEras.map((era) => {
                const isSelected = selectedEras.includes(era);
                return (
                  <button
                    key={era}
                    onClick={() => toggleEra(era)}
                    className={`rounded-lg px-3 py-2 text-sm font-bold uppercase tracking-wide transition-colors ${
                      isSelected
                        ? 'bg-cinema-red text-white shadow-[0_0_15px_rgba(229,9,20,0.5)]'
                        : 'bg-white/5 text-white/80 border border-white/10 hover:bg-white/10'
                    }`}
                    data-testid={`era-option-${era.toLowerCase().replace(/\+/g, 'plus')}`}
                  >
                    {era}
                  </button>
                );
              })}
            </div>
          </div>

          <button
            onClick={startWithSelectedGenres}
            className="w-full bg-cinema-red text-white rounded-full py-4 font-bold uppercase tracking-widest hover:bg-red-700 transition-colors shadow-[0_0_15px_rgba(229,9,20,0.5)]"
            data-testid="start-with-categories-btn"
          >
            Start Swiping
          </button>
        </div>
      </div>
    );
  }

  if (movies.length === 0) {
    return (
      <div className="min-h-screen bg-cinema-black film-grain flex items-center justify-center p-4">
        <div className="text-center space-y-4">
          <h2 className="font-secondary text-3xl text-white tracking-wide uppercase" data-testid="loading-movies-title">
            {waitingForMembers ? "Waiting For Others..." : "Loading Movies..."}
          </h2>
          <p className="text-white/60 text-sm" data-testid="loading-movies-subtitle">
            {waitingForMembers
              ? `${selectedMembers}/${totalMembers} members selected categories. Building a merged list.`
              : "Getting picks for your selected categories."}
          </p>
        </div>
      </div>
    );
  }

  if (currentIndex >= movies.length) {
    return (
      <div className="min-h-screen bg-cinema-black film-grain flex items-center justify-center p-4">
        <div className="text-center space-y-4">
          <h2 className="font-secondary text-4xl text-white tracking-wide uppercase">No More Movies!</h2>
          <button
            onClick={() => navigate(`/room/${roomCode}`)}
            className="bg-cinema-red text-white rounded-full px-8 py-4 font-bold uppercase tracking-widest hover:bg-red-700 transition-colors shadow-[0_0_15px_rgba(229,9,20,0.5)]"
          >
            Back to Room
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-cinema-black film-grain flex items-center justify-center p-4">
      <div className="max-w-md w-full h-[600px] relative">
        <AnimatePresence>
          <MovieCard 
            key={currentIndex}
            movie={movies[currentIndex]} 
            onSwipe={handleSwipe}
          />
        </AnimatePresence>
        
        <div className="absolute -bottom-20 left-0 right-0 flex justify-center gap-6">
          <button
            onClick={() => handleSwipe('dislike')}
            className="w-16 h-16 rounded-full bg-white/10 hover:bg-white/20 border-2 border-white/20 flex items-center justify-center transition-colors"
            data-testid="dislike-btn"
          >
            <span className="text-3xl">✕</span>
          </button>
          <button
            onClick={() => handleSwipe('like')}
            className="w-16 h-16 rounded-full bg-cinema-red hover:bg-red-700 flex items-center justify-center transition-colors shadow-[0_0_15px_rgba(229,9,20,0.5)]"
            data-testid="like-btn"
          >
            <span className="text-3xl">❤</span>
          </button>
        </div>
      </div>

      <AnimatePresence>
        {showMatch && matchedMovie && (
          <motion.div
            className="fixed inset-0 bg-black/90 backdrop-blur-xl flex items-center justify-center z-50 p-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            data-testid="match-popup"
          >
            <motion.div
              className="max-w-md w-full text-center space-y-6"
              initial={{ scale: 0.5, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: "spring", bounce: 0.5 }}
            >
              <h2 className="font-secondary text-6xl text-cinema-red tracking-wide uppercase" data-testid="match-title">It's a Match 🎬</h2>
              <div className="w-64 h-96 mx-auto rounded-xl overflow-hidden" style={{ boxShadow: '0 0 60px rgba(229, 9, 20, 0.8)' }}>
                <img src={matchedMovie.poster} alt={matchedMovie.title} className="w-full h-full object-cover" data-testid="matched-movie-poster" />
              </div>
              <div className="space-y-2">
                <h3 className="font-secondary text-3xl text-white tracking-wide uppercase" data-testid="matched-movie-title">{matchedMovie.title}</h3>
                <p className="text-cinema-gold font-bold" data-testid="matched-movie-year">{matchedMovie.year} • {matchedMovie.genre}</p>
              </div>
              <button
                onClick={() => setShowMatch(false)}
                className="bg-cinema-red text-white rounded-full px-8 py-4 font-bold uppercase tracking-widest hover:bg-red-700 transition-colors shadow-[0_0_15px_rgba(229,9,20,0.5)]"
                data-testid="close-match-btn"
              >
                Keep Swiping
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <Toaster position="top-center" theme="dark" />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/room/:roomCode" element={<Room />} />
          <Route path="/swipe/:roomCode" element={<Swipe />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;