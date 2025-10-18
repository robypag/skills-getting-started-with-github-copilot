"""
Performance and load tests for the High School Management System API.
"""

import pytest
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.app import activities


class TestPerformance:
    """Performance tests for API endpoints."""
    
    def test_get_activities_response_time(self, client, reset_activities):
        """Test that getting activities responds within reasonable time."""
        start_time = time.time()
        response = client.get("/activities")
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 1.0, f"Response time {response_time}s exceeds 1 second threshold"
    
    def test_signup_response_time(self, client, reset_activities):
        """Test that signup responds within reasonable time."""
        start_time = time.time()
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "performance@mergington.edu"}
        )
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 1.0, f"Signup response time {response_time}s exceeds 1 second threshold"
    
    def test_multiple_rapid_requests(self, client, reset_activities):
        """Test handling multiple rapid requests to different endpoints."""
        start_time = time.time()
        
        # Make multiple requests rapidly
        responses = []
        for i in range(10):
            if i % 2 == 0:
                response = client.get("/activities")
            else:
                response = client.post(
                    "/activities/Chess Club/signup",
                    params={"email": f"user{i}@mergington.edu"}
                )
            responses.append(response)
        
        end_time = time.time()
        
        # Check that all requests completed
        assert len(responses) == 10
        
        # Check that most requests succeeded (some signups might fail due to duplicates)
        success_count = sum(1 for r in responses if r.status_code in [200, 400])
        assert success_count >= 8, "Most requests should succeed"
        
        # Check total time is reasonable
        total_time = end_time - start_time
        assert total_time < 5.0, f"Total time {total_time}s for 10 requests exceeds 5 second threshold"


class TestLoadHandling:
    """Tests for handling increased load."""
    
    def test_many_participants_in_activity(self, client, reset_activities):
        """Test performance with many participants in an activity."""
        # Note: The current API doesn't enforce participant limits, so we test performance only
        base_email = "loadtest{i}@mergington.edu"
        num_participants = 20  # Reduced number for performance testing
        
        successful_signups = 0
        for i in range(num_participants):
            email = base_email.format(i=i)
            response = client.post(
                "/activities/Gym Class/signup",
                params={"email": email}
            )
            if response.status_code == 200:
                successful_signups += 1
        
        # Verify that signups worked (API doesn't enforce limits currently)
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        gym_participants = activities_data["Gym Class"]["participants"]
        
        # Should have original participants plus new ones
        # Gym Class starts with 2 participants
        expected_min = 2 + successful_signups
        assert len(gym_participants) >= expected_min
        assert successful_signups > 0, "At least some signups should succeed"
    
    def test_large_activity_list_performance(self, client):
        """Test performance when retrieving a large list of activities."""
        # Manually trigger the startup event to add additional activities
        from src.app import _merge_additional_activities
        _merge_additional_activities()
        
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        
        # Should have original 3 + 6 additional = 9 activities after startup
        assert len(data) >= 9, f"Should have at least 9 activities after startup, got {len(data)}"
        
        # Test that response is still fast even with more activities
        start_time = time.time()
        for _ in range(5):
            response = client.get("/activities")
            assert response.status_code == 200
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 5
        assert avg_time < 0.5, f"Average response time {avg_time}s is too slow"


class TestConcurrency:
    """Tests for concurrent access scenarios."""
    
    @pytest.mark.slow
    def test_concurrent_signups_different_activities(self, client, reset_activities):
        """Test concurrent signups to different activities."""
        def signup_worker(activity_name, email):
            return client.post(
                f"/activities/{activity_name}/signup",
                params={"email": email}
            )
        
        # Prepare concurrent requests
        requests = [
            ("Chess Club", "concurrent1@mergington.edu"),
            ("Programming Class", "concurrent2@mergington.edu"),
            ("Gym Class", "concurrent3@mergington.edu"),
            ("Chess Club", "concurrent4@mergington.edu"),
            ("Programming Class", "concurrent5@mergington.edu"),
        ]
        
        # Execute concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(signup_worker, activity, email) 
                      for activity, email in requests]
            
            responses = [future.result() for future in as_completed(futures)]
        
        # All should succeed since they're for different participants
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count == len(requests), "All concurrent signups should succeed"
    
    @pytest.mark.slow
    def test_concurrent_operations_same_activity(self, client, reset_activities):
        """Test concurrent operations on the same activity."""
        def mixed_operations():
            operations = []
            
            # Mix of signups and gets
            for i in range(3):
                operations.append(("signup", f"concurrent{i}@mergington.edu"))
            for i in range(2):
                operations.append(("get", None))
            
            return operations
        
        def operation_worker(op_type, email):
            if op_type == "signup":
                return client.post(
                    "/activities/Chess Club/signup",
                    params={"email": email}
                )
            else:  # get
                return client.get("/activities")
        
        operations = mixed_operations()
        
        # Execute concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(operation_worker, op_type, email) 
                      for op_type, email in operations]
            
            responses = [future.result() for future in as_completed(futures)]
        
        # All GET requests should succeed
        get_responses = [r for r in responses if r.url.path == "/activities"]
        assert all(r.status_code == 200 for r in get_responses)
        
        # Some signup requests should succeed
        signup_responses = [r for r in responses if "signup" in str(r.url)]
        success_signups = sum(1 for r in signup_responses if r.status_code == 200)
        assert success_signups > 0, "At least some signups should succeed"


class TestMemoryUsage:
    """Tests for memory usage patterns."""
    
    def test_activities_data_persistence(self, client, reset_activities):
        """Test that activities data persists across requests."""
        # Sign up a user
        email = "persistence@mergington.edu"
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response.status_code == 200
        
        # Make several other requests
        for _ in range(5):
            client.get("/activities")
        
        # Verify the user is still signed up
        response = client.get("/activities")
        data = response.json()
        assert email in data["Chess Club"]["participants"]
    
    def test_no_memory_leaks_in_repeated_operations(self, client, reset_activities):
        """Test for potential memory leaks in repeated operations."""
        # Perform many signup/unregister cycles
        email = "memory@mergington.edu"
        
        for i in range(10):
            # Signup
            signup_response = client.post(
                "/activities/Chess Club/signup",
                params={"email": email}
            )
            assert signup_response.status_code == 200
            
            # Unregister
            unregister_response = client.delete(f"/activities/Chess Club/participants/{email}")
            assert unregister_response.status_code == 200
        
        # Verify final state is clean
        response = client.get("/activities")
        data = response.json()
        assert email not in data["Chess Club"]["participants"]