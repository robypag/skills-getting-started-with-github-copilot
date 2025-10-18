"""
Tests for data models and edge cases in the High School Management System.
"""

import pytest
from src.app import activities, _additional_activities, _merge_additional_activities


class TestDataModels:
    """Tests for the activities data structure and validation."""
    
    def test_activities_structure(self, reset_activities):
        """Test that activities have the correct structure."""
        for activity_name, activity_data in activities.items():
            assert isinstance(activity_name, str)
            assert isinstance(activity_data, dict)
            
            # Check required fields
            required_fields = ["description", "schedule", "max_participants", "participants"]
            for field in required_fields:
                assert field in activity_data, f"Missing field {field} in {activity_name}"
            
            # Check field types
            assert isinstance(activity_data["description"], str)
            assert isinstance(activity_data["schedule"], str)
            assert isinstance(activity_data["max_participants"], int)
            assert isinstance(activity_data["participants"], list)
            
            # Check that participants are strings (email addresses)
            for participant in activity_data["participants"]:
                assert isinstance(participant, str)
                assert "@" in participant  # Basic email validation
    
    def test_additional_activities_structure(self):
        """Test that additional activities have the correct structure."""
        for activity_name, activity_data in _additional_activities.items():
            assert isinstance(activity_name, str)
            assert isinstance(activity_data, dict)
            
            # Check required fields
            required_fields = ["description", "schedule", "max_participants", "participants"]
            for field in required_fields:
                assert field in activity_data, f"Missing field {field} in {activity_name}"
    
    def test_merge_additional_activities_function(self, reset_activities):
        """Test the merge additional activities function."""
        # Get initial count
        initial_count = len(activities)
        
        # Call the merge function
        _merge_additional_activities()
        
        # Check that additional activities were added
        final_count = len(activities)
        assert final_count > initial_count
        
        # Check that original activities are still present
        assert "Chess Club" in activities
        assert "Programming Class" in activities
        assert "Gym Class" in activities
        
        # Check that additional activities were added
        for activity_name in _additional_activities:
            assert activity_name in activities


class TestEdgeCases:
    """Tests for edge cases and error conditions."""
    
    def test_activity_name_with_special_characters(self, client, reset_activities):
        """Test handling activity names with special characters in URLs."""
        # Try to access an activity with URL-encoded characters
        response = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 200
    
    def test_email_validation_edge_cases(self, client, reset_activities):
        """Test various email formats."""
        test_emails = [
            "simple@mergington.edu",
            "user.name@mergington.edu",
            "user+tag@mergington.edu",
            "123@mergington.edu"
        ]
        
        for email in test_emails:
            response = client.post(
                "/activities/Chess Club/signup",
                params={"email": email}
            )
            assert response.status_code in [200, 400]  # Either success or validation error
    
    def test_case_sensitivity_activity_names(self, client, reset_activities):
        """Test case sensitivity in activity names."""
        # Test with different case
        response = client.post(
            "/activities/chess club/signup",  # lowercase
            params={"email": "test@mergington.edu"}
        )
        # Should return 404 because activity names are case-sensitive
        assert response.status_code == 404
    
    def test_empty_parameters(self, client, reset_activities):
        """Test handling of empty parameters."""
        # Test empty email
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": ""}
        )
        # Should handle gracefully (exact behavior depends on FastAPI validation)
        assert response.status_code in [200, 400, 422]
    
    def test_unicode_in_email(self, client, reset_activities):
        """Test handling of unicode characters in email."""
        unicode_email = "tëst@mergington.edu"
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": unicode_email}
        )
        # Should handle gracefully
        assert response.status_code in [200, 400, 422]


class TestParticipantLimits:
    """Tests related to participant limits and capacity."""
    
    def test_activity_has_max_participants_field(self, reset_activities):
        """Test that all activities have max_participants defined."""
        for activity_name, activity_data in activities.items():
            assert "max_participants" in activity_data
            assert isinstance(activity_data["max_participants"], int)
            assert activity_data["max_participants"] > 0
    
    def test_current_participant_count_vs_max(self, reset_activities):
        """Test that current participants don't exceed maximum."""
        for activity_name, activity_data in activities.items():
            current_count = len(activity_data["participants"])
            max_participants = activity_data["max_participants"]
            assert current_count <= max_participants, f"{activity_name} has {current_count} participants but max is {max_participants}"


class TestConcurrencyScenarios:
    """Tests for potential concurrency issues."""
    
    def test_rapid_signup_same_email(self, client, reset_activities):
        """Test rapid successive signups with the same email."""
        email = "rapid@mergington.edu"
        
        # Make multiple rapid requests (simulating concurrent access)
        responses = []
        for _ in range(3):
            response = client.post(
                "/activities/Chess Club/signup",
                params={"email": email}
            )
            responses.append(response)
        
        # Only one should succeed, others should fail with 400
        success_count = sum(1 for r in responses if r.status_code == 200)
        failure_count = sum(1 for r in responses if r.status_code == 400)
        
        assert success_count == 1, "Exactly one signup should succeed"
        assert failure_count == 2, "Two signups should fail due to duplicate"
    
    def test_signup_and_unregister_race(self, client, reset_activities):
        """Test signup followed immediately by unregistration."""
        email = "race@mergington.edu"
        
        # Signup
        signup_response = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert signup_response.status_code == 200
        
        # Immediate unregister
        unregister_response = client.delete(f"/activities/Chess Club/participants/{email}")
        assert unregister_response.status_code == 200
        
        # Verify final state
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data["Chess Club"]["participants"]