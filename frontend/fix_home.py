import re

with open("src/App.js", "r") as f:
    content = f.read()

# 1. Add state variable
old_state = """  const [username, setUsername] = useState(localStorage.getItem('username') || "");
  const [roomCode, setRoomCode] = useState("");
  const [mode, setMode] = useState(null);"""

new_state = """  const [username, setUsername] = useState(localStorage.getItem('username') || "");
  const [roomCode, setRoomCode] = useState("");
  const [mode, setMode] = useState(null);
  const [includeAdult, setIncludeAdult] = useState(false);"""
content = content.replace(old_state, new_state)

# 2. Add to handleCreateRoom
old_create = """  const handleCreateRoom = async () => {
    if (!username.trim()) {
      toast.error("Please enter your name");
      return;
    }

    try {
      const response = await axios.post(`${API}/rooms/create`, { username });"""

new_create = """  const handleCreateRoom = async () => {
    if (!username.trim()) {
      toast.error("Please enter your name");
      return;
    }

    try {
      const response = await axios.post(`${API}/rooms/create`, { 
        username,
        include_adult: includeAdult
      });"""
content = content.replace(old_create, new_create)

# 3. Add to the UI (mode === "create")
old_ui = """                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoFocus
              />
              <button
                onClick={handleCreateRoom}
                className="w-full bg-cinema-red text-white rounded-lg py-3 font-bold uppercase tracking-wider hover:bg-red-700 transition duration-300 shadow-[0_0_15px_rgba(229,9,20,0.4)]"
                data-testid="create-room-submit"
              >
                Create Room
              </button>"""

new_ui = """                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoFocus
              />
              <label className="flex items-center space-x-3 cursor-pointer py-2 px-1">
                <input 
                  type="checkbox"
                  checked={includeAdult}
                  onChange={(e) => setIncludeAdult(e.target.checked)}
                  className="w-5 h-5 accent-cinema-red rounded border-white/20 bg-white/10"
                  data-testid="include-adult-checkbox"
                />
                <span className="text-white/70 text-sm">Include Adult (18+) Movies</span>
              </label>
              <button
                onClick={handleCreateRoom}
                className="w-full mt-2 bg-cinema-red text-white rounded-lg py-3 font-bold uppercase tracking-wider hover:bg-red-700 transition duration-300 shadow-[0_0_15px_rgba(229,9,20,0.4)]"
                data-testid="create-room-submit"
              >
                Create Room
              </button>"""
content = content.replace(old_ui, new_ui)

with open("src/App.js", "w") as f:
    f.write(content)
