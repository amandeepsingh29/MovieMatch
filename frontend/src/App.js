import { useState, useEffect } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route, useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import { motion, useMotionValue, useTransform, AnimatePresence } from "framer-motion";
import { Film, Users, Copy, Check } from "lucide-react";
import { Toaster, toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
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

  useEffect(() => {
    if (!userId) {
      navigate('/');
      return;
    }

    loadRoom();
    const ws = new WebSocket(`${WS_URL}/ws/${roomCode}`);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'member_joined') {
        loadRoom();
        toast.success(`${data.username} joined the room!`);
      } else if (data.type === 'room_started') {
        navigate(`/swipe/${roomCode}`);
      }
    };

    return () => ws.close();
  }, [roomCode]);

  const loadRoom = async () => {
    try {
      const response = await axios.get(`${API}/rooms/${roomCode}`);
      setRoom(response.data);
    } catch (error) {
      toast.error("Room not found");
      navigate('/');
    }
  };

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

  if (!room) return null;

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
        <img 
          src={movie.poster} 
          alt={movie.title} 
          className="w-full h-full object-cover"
        />
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black via-black/80 to-transparent p-6 space-y-2">
          <h3 className="font-secondary text-3xl text-white tracking-wide uppercase" data-testid="movie-title">{movie.title}</h3>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-cinema-gold font-bold" data-testid="movie-year">{movie.year}</span>
            <span className="text-white/50">•</span>
            <span className="text-white/70" data-testid="movie-genre">{movie.genre}</span>
          </div>
        </div>
        
        {movie.trailer && (
          <div className="absolute top-4 right-4">
            <div className="w-32 h-20 rounded-lg overflow-hidden border-2 border-white/20">
              <iframe
                src={`https://www.youtube.com/embed/${movie.trailer}?autoplay=1&mute=1&controls=0&loop=1&playlist=${movie.trailer}`}
                className="w-full h-full"
                allow="autoplay"
              />
            </div>
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
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showMatch, setShowMatch] = useState(false);
  const [matchedMovie, setMatchedMovie] = useState(null);
  const [userId, setUserId] = useState(localStorage.getItem('user_id'));

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

    loadMovies();
    
    const ws = new WebSocket(`${WS_URL}/ws/${roomCode}`);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'match') {
        setMatchedMovie(data.movie);
        setShowMatch(true);
      }
    };

    return () => ws.close();
  }, [roomCode]);

  const loadMovies = async () => {
    try {
      const response = await axios.get(`${API}/movies`);
      setMovies(response.data);
    } catch (error) {
      toast.error("Failed to load movies");
    }
  };

  const handleSwipe = async (direction) => {
    const movie = movies[currentIndex];
    
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

  if (movies.length === 0) return null;
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