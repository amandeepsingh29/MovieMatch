import requests
import sys
import json
from datetime import datetime
import time

class MovieMatchAPITester:
    def __init__(self, base_url="https://reel-decide.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.room_code = None
        self.user_ids = []
        self.usernames = []

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        if data:
            print(f"   Data: {json.dumps(data, indent=2)}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)

            print(f"   Response Status: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)}")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_create_room(self, username):
        """Test room creation"""
        success, response = self.run_test(
            "Create Room",
            "POST",
            "rooms/create",
            200,
            data={"username": username}
        )
        if success and 'room_code' in response:
            self.room_code = response['room_code']
            self.user_ids.append(response['user_id'])
            self.usernames.append(username)
            print(f"   Room Code: {self.room_code}")
            print(f"   User ID: {response['user_id']}")
            return True
        return False

    def test_join_room(self, username, room_code):
        """Test joining a room"""
        success, response = self.run_test(
            "Join Room",
            "POST",
            "rooms/join",
            200,
            data={"username": username, "room_code": room_code}
        )
        if success and 'user_id' in response:
            self.user_ids.append(response['user_id'])
            self.usernames.append(username)
            print(f"   User ID: {response['user_id']}")
            return True
        return False

    def test_join_nonexistent_room(self, username):
        """Test joining a non-existent room"""
        success, response = self.run_test(
            "Join Non-existent Room",
            "POST",
            "rooms/join",
            404,
            data={"username": username, "room_code": "FAKE99"}
        )
        return success

    def test_get_room(self, room_code):
        """Test getting room details"""
        success, response = self.run_test(
            "Get Room Details",
            "GET",
            f"rooms/{room_code}",
            200
        )
        if success:
            print(f"   Members: {len(response.get('members', []))}")
            for i, member in enumerate(response.get('members', [])):
                print(f"     {i+1}. {member.get('username')} (ID: {member.get('user_id')})")
        return success

    def test_get_nonexistent_room(self):
        """Test getting non-existent room"""
        success, response = self.run_test(
            "Get Non-existent Room",
            "GET",
            "rooms/FAKE99",
            404
        )
        return success

    def test_start_swiping(self, room_code):
        """Test starting swiping session"""
        success, response = self.run_test(
            "Start Swiping",
            "POST",
            "rooms/start",
            200,
            data={"room_code": room_code}
        )
        return success

    def test_get_movies(self):
        """Test getting movie list"""
        success, response = self.run_test(
            "Get Movies",
            "GET",
            "movies",
            200
        )
        if success:
            movies = response if isinstance(response, list) else []
            print(f"   Movies count: {len(movies)}")
            if movies:
                print(f"   First movie: {movies[0].get('title')} ({movies[0].get('year')})")
        return success, response if isinstance(response, list) else []

    def test_record_swipe(self, room_code, user_id, movie_id, direction):
        """Test recording a swipe"""
        success, response = self.run_test(
            f"Record Swipe ({direction})",
            "POST",
            "swipe",
            200,
            data={
                "room_code": room_code,
                "user_id": user_id,
                "movie_id": movie_id,
                "direction": direction
            }
        )
        return success

    def test_get_matches(self, room_code):
        """Test getting matches for a room"""
        success, response = self.run_test(
            "Get Matches",
            "GET",
            f"matches/{room_code}",
            200
        )
        if success:
            matches = response if isinstance(response, list) else []
            print(f"   Matches count: {len(matches)}")
            for match in matches:
                movie = match.get('movie', {})
                print(f"     Match: {movie.get('title')} ({movie.get('year')})")
        return success, response if isinstance(response, list) else []

    def test_match_detection(self, room_code, user_ids, movie_id):
        """Test match detection when all users like the same movie"""
        print(f"\n🎬 Testing Match Detection for movie {movie_id}...")
        
        # All users like the same movie
        for i, user_id in enumerate(user_ids):
            success = self.test_record_swipe(room_code, user_id, movie_id, "like")
            if not success:
                return False
            
        # Check if match was created
        time.sleep(1)  # Give time for match processing
        success, matches = self.test_get_matches(room_code)
        
        if success and matches:
            # Check if our movie is in matches
            matched_movie_ids = [match.get('movie_id') for match in matches]
            if movie_id in matched_movie_ids:
                print(f"✅ Match detected successfully for movie {movie_id}")
                return True
            else:
                print(f"❌ Match not found for movie {movie_id}")
                return False
        else:
            print(f"❌ No matches found or error getting matches")
            return False

def main():
    print("🎬 MovieMatch API Testing Suite")
    print("=" * 50)
    
    # Setup
    tester = MovieMatchAPITester()
    
    # Test basic endpoints first
    print("\n📡 Testing Basic Endpoints...")
    
    # Test get movies (should work without room)
    success, movies = tester.test_get_movies()
    if not success or not movies:
        print("❌ Movies endpoint failed, stopping tests")
        return 1
    
    # Test room creation
    print("\n🏠 Testing Room Management...")
    
    if not tester.test_create_room("Alice"):
        print("❌ Room creation failed, stopping tests")
        return 1
    
    room_code = tester.room_code
    
    # Test getting room details
    if not tester.test_get_room(room_code):
        print("❌ Get room failed")
        return 1
    
    # Test joining room
    if not tester.test_join_room("Bob", room_code):
        print("❌ Join room failed")
        return 1
    
    # Test error cases
    print("\n🚫 Testing Error Cases...")
    tester.test_join_nonexistent_room("Charlie")
    tester.test_get_nonexistent_room()
    
    # Test starting swiping
    print("\n🎯 Testing Swiping Flow...")
    if not tester.test_start_swiping(room_code):
        print("❌ Start swiping failed")
        return 1
    
    # Test swipe recording
    movie_id = movies[0]['id']  # Use first movie
    
    # Test individual swipes
    alice_id = tester.user_ids[0]
    bob_id = tester.user_ids[1]
    
    # Alice dislikes first movie
    tester.test_record_swipe(room_code, alice_id, movie_id, "dislike")
    
    # Bob likes first movie  
    tester.test_record_swipe(room_code, bob_id, movie_id, "like")
    
    # Test match detection with second movie
    if len(movies) > 1:
        match_movie_id = movies[1]['id']
        if not tester.test_match_detection(room_code, tester.user_ids, match_movie_id):
            print("❌ Match detection failed")
    
    # Test getting matches
    tester.test_get_matches(room_code)
    
    # Print final results
    print(f"\n📊 Test Results:")
    print(f"Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())