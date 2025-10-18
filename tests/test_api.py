"""
Tests for the High School Management System API endpoints.
"""

import pytest
from fastapi import status
from src.app import activities


class TestRootEndpoint:
    """Tests for the root endpoint."""
    
    def test_root_redirects_to_static_index(self, client):
        """Test that root endpoint redirects to static index.html."""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
        assert response.headers["location"] == "/static/index.html"


class TestActivitiesEndpoint:
    """Tests for the activities endpoint."""
    
    def test_get_activities_returns_all_activities(self, client, reset_activities):
        """Test that GET /activities returns all available activities."""
        response = client.get("/activities")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert isinstance(data, dict)
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
        
        # Verify structure of an activity
        chess_club = data["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        assert isinstance(chess_club["participants"], list)
    
    def test_get_activities_includes_additional_activities_after_startup(self, client):
        """Test that additional activities are included after startup event."""
        # Import and manually trigger the startup function to ensure it runs
        from src.app import _merge_additional_activities
        _merge_additional_activities()
        
        response = client.get("/activities")
        data = response.json()
        
        # Check for additional activities that should be merged at startup
        expected_additional = [
            "Soccer Team", "Track and Field", "Drama Club", 
            "Ceramics Studio", "Robotics Club", "Debate Team"
        ]
        
        for activity_name in expected_additional:
            assert activity_name in data, f"Expected activity {activity_name} not found"


class TestActivitySignup:
    """Tests for activity signup functionality."""
    
    def test_signup_for_existing_activity_success(self, client, reset_activities):
        """Test successful signup for an existing activity."""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Signed up newstudent@mergington.edu for Chess Club"
        
        # Verify the participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        chess_participants = activities_data["Chess Club"]["participants"]
        assert "newstudent@mergington.edu" in chess_participants
    
    def test_signup_for_nonexistent_activity_fails(self, client, reset_activities):
        """Test that signing up for a non-existent activity returns 404."""
        response = client.post(
            "/activities/Nonexistent Club/signup",
            params={"email": "student@mergington.edu"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_signup_duplicate_participant_fails(self, client, reset_activities):
        """Test that signing up the same participant twice fails."""
        email = "michael@mergington.edu"  # Already in Chess Club
        
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["detail"] == "Student already signed up for this activity"
    
    def test_signup_multiple_different_participants(self, client, reset_activities):
        """Test signing up multiple different participants to the same activity."""
        emails = ["student1@mergington.edu", "student2@mergington.edu", "student3@mergington.edu"]
        
        for email in emails:
            response = client.post(
                "/activities/Chess Club/signup",
                params={"email": email}
            )
            assert response.status_code == status.HTTP_200_OK
        
        # Verify all participants were added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        chess_participants = activities_data["Chess Club"]["participants"]
        
        for email in emails:
            assert email in chess_participants


class TestParticipantUnregistration:
    """Tests for participant unregistration functionality."""
    
    def test_unregister_existing_participant_success(self, client, reset_activities):
        """Test successful unregistration of an existing participant."""
        email = "michael@mergington.edu"  # Existing participant in Chess Club
        
        response = client.delete(f"/activities/Chess Club/participants/{email}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == f"Unregistered {email} from Chess Club"
        
        # Verify the participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        chess_participants = activities_data["Chess Club"]["participants"]
        assert email not in chess_participants
    
    def test_unregister_from_nonexistent_activity_fails(self, client, reset_activities):
        """Test that unregistering from a non-existent activity returns 404."""
        response = client.delete("/activities/Nonexistent Club/participants/student@mergington.edu")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_unregister_nonexistent_participant_fails(self, client, reset_activities):
        """Test that unregistering a non-existent participant returns 404."""
        email = "nonexistent@mergington.edu"
        
        response = client.delete(f"/activities/Chess Club/participants/{email}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "Participant not found in this activity"
    
    def test_unregister_and_signup_again(self, client, reset_activities):
        """Test unregistering a participant and then signing them up again."""
        email = "michael@mergington.edu"  # Existing participant in Chess Club
        
        # First, unregister
        response = client.delete(f"/activities/Chess Club/participants/{email}")
        assert response.status_code == status.HTTP_200_OK
        
        # Then, sign up again
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response.status_code == status.HTTP_200_OK
        
        # Verify the participant is back in the list
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        chess_participants = activities_data["Chess Club"]["participants"]
        assert email in chess_participants


class TestIntegrationScenarios:
    """Integration tests for common user scenarios."""
    
    def test_complete_activity_lifecycle(self, client, reset_activities):
        """Test a complete lifecycle: view activities, signup, unregister."""
        email = "lifecycle@mergington.edu"
        activity = "Programming Class"
        
        # 1. Get initial activities
        response = client.get("/activities")
        assert response.status_code == status.HTTP_200_OK
        initial_data = response.json()
        initial_participants = len(initial_data[activity]["participants"])
        
        # 2. Sign up for activity
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response.status_code == status.HTTP_200_OK
        
        # 3. Verify signup
        response = client.get("/activities")
        after_signup_data = response.json()
        assert len(after_signup_data[activity]["participants"]) == initial_participants + 1
        assert email in after_signup_data[activity]["participants"]
        
        # 4. Unregister
        response = client.delete(f"/activities/{activity}/participants/{email}")
        assert response.status_code == status.HTTP_200_OK
        
        # 5. Verify unregistration
        response = client.get("/activities")
        after_unregister_data = response.json()
        assert len(after_unregister_data[activity]["participants"]) == initial_participants
        assert email not in after_unregister_data[activity]["participants"]
    
    def test_multiple_activities_signup(self, client, reset_activities):
        """Test signing up the same student for multiple different activities."""
        email = "multisport@mergington.edu"
        activities_to_join = ["Chess Club", "Programming Class", "Gym Class"]
        
        for activity in activities_to_join:
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": email}
            )
            assert response.status_code == status.HTTP_200_OK
        
        # Verify the student is in all activities
        response = client.get("/activities")
        data = response.json()
        
        for activity in activities_to_join:
            assert email in data[activity]["participants"]