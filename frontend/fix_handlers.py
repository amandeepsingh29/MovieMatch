import re

with open("frontend/src/App.js", "r") as f:
    content = f.read()

# Handle preferences_updated
old_pref = """        } else if (data.type === 'preferences_updated' && selectionSubmitted) {
          loadRoomMovies();
        }"""
new_pref = """        } else if (data.type === 'preferences_updated' && selectionSubmitted) {
          loadRoomMovies(1);
          setPage(1);
          setCurrentIndex(0);
        }"""
content = content.replace(old_pref, new_pref)

# Handle reconnect
old_reconnect = """        wsReconnectTimerRef.current = setTimeout(() => {
          if (!intentionalClose) {
            connectWebSocket();
            if (selectionSubmitted) {
              loadRoomMovies();
            }
          }
        }, 3000);"""
new_reconnect = """        wsReconnectTimerRef.current = setTimeout(() => {
          if (!intentionalClose) {
            connectWebSocket();
            // Don't arbitrarily reload movies on reconnect unless we are still waiting
            if (selectionSubmitted && waitingForMembers) {
              loadRoomMovies(1);
            }
          }
        }, 3000);"""
content = content.replace(old_reconnect, new_reconnect)

# Handle visibility
old_vis = """    const handleVisibilityOrFocus = () => {
      if (document.visibilityState === 'visible' && selectionSubmitted) {
        loadRoomMovies();
      }
    };"""
new_vis = """    const handleVisibilityOrFocus = () => {
      if (document.visibilityState === 'visible' && selectionSubmitted && waitingForMembers) {
        loadRoomMovies(1);
      }
    };"""
content = content.replace(old_vis, new_vis)

# Handle waiting polling
old_poll = """    const timer = setInterval(() => {
      loadRoomMovies();
    }, 2000);"""
new_poll = """    const timer = setInterval(() => {
      loadRoomMovies(1);
    }, 2000);"""
content = content.replace(old_poll, new_poll)


# Double check our new pagination loadRoomMovies doesn't have stale closures for page state
# Using functional updates where applicable, but we already added setPage state.
with open("frontend/src/App.js", "w") as f:
    f.write(content)

