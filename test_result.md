#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: "there are many issues in the app - find and fix them"
backend:
	- task: "Room and swipe API validation hardening"
		implemented: true
		working: true
		file: "backend/server.py"
		stuck_count: 0
		priority: "high"
		needs_retesting: false
		status_history:
			- working: false
				agent: "user"
				comment: "User reported many issues in the app."
			- working: true
				agent: "main"
				comment: "Added validation for username, room state, room membership, swipe direction, and deduplicated swipes with upsert."
			- working: true
				agent: "main"
				comment: "Local integration suite passed 9/9 checks including create/join/start/swipe/match and websocket connectivity."
frontend:
	- task: "Frontend effect and connection stability"
		implemented: true
		working: true
		file: "frontend/src/App.js"
		stuck_count: 0
		priority: "high"
		needs_retesting: false
		status_history:
			- working: false
				agent: "user"
				comment: "Punjabi movies are not showing poster images and trailers."
			- working: false
				agent: "user"
				comment: "Requested two more pre-swipe questions: preferred language (Hindi/English/Punjabi) and one more relevant preference."
			- working: false
				agent: "user"
				comment: "Movie list should be merged across all users' selected categories, not filtered per user individually."
			- working: false
				agent: "user"
				comment: "After clicking Start Swiping, screen turns black/frozen."
			- working: false
				agent: "user"
				comment: "User reports repeated 'Connection issue detected. Please refresh.' toast spam."
			- working: true
				agent: "main"
				comment: "Fixed hook dependency issues, added backend URL fallback, and improved websocket error handling in Room and Swipe flows."
			- working: true
				agent: "main"
				comment: "Frontend now compiles successfully with no warnings in the active dev server."
			- working: true
				agent: "main"
				comment: "Updated websocket handling to suppress cleanup/dev-mode disconnect noise and show disconnect toasts only once for unexpected closures."
			- working: true
				agent: "main"
				comment: "Fixed swipe-page blank screen by rendering genre picker before movie-empty checks and showing a loading UI fallback instead of returning null."
			- working: true
				agent: "main"
				comment: "Implemented room-level genre preferences and merged movie collection so all members get the same union of selected categories."
			- working: true
				agent: "main"
				comment: "Added two more questions before swiping: preferred language and release era, and updated room-level merged filtering to include genres + languages + eras."
			- working: true
				agent: "main"
				comment: "Expanded movie library from 14 to 40 titles with broader genres and languages to improve recommendation variety."
			- working: true
				agent: "main"
				comment: "Added movie-card fallbacks so broken poster URLs show a styled placeholder and trailer preview hides on load failure instead of appearing broken."
			- working: true
				agent: "main"
				comment: "Generated stable fallback poster URLs and trailer search URLs for every movie, and updated UI to open trailer links instead of relying on fragile embed IDs."
			- working: true
				agent: "main"
				comment: "Switched non-English movie posters from broken TMDB paths to picsum.photos seeded image URLs so poster fetches no longer fail."
			- working: true
				agent: "main"
				comment: "Replaced placeholder non-English posters with movie-accurate TMDB web poster URLs for Punjabi/Hindi titles and removed forced picsum override."
			- working: true
				agent: "main"
				comment: "Expanded movie library per category target by generating deterministic variants so each genre category now has at least 100 entries (1000 total)."
metadata:
	created_by: "main_agent"
	version: "1.0"
	test_sequence: 2
	run_ui: false
test_plan:
	current_focus:
		- "Room and swipe API validation hardening"
		- "Frontend effect and connection stability"
	stuck_tasks: []
	test_all: true
	test_priority: "high_first"
agent_communication:
	- agent: "main"
		message: "Implemented stability and validation fixes in backend and frontend; completed local retest with all critical checks passing."