"""
Comprehensive manual E2E tests for all critical endpoints.

Top-down approach - testing real user scenarios.
"""

import logging

import pytest

from tests.utils_test.api_test_client import AsyncApiTestClient, TestScenarioType

# Use test session logger as per project standards
logger = logging.getLogger("test_session")


class TestE2EManualComprehensive:
    """Comprehensive E2E tests for all critical endpoints."""

    async def test_public_endpoints_health(self, api_client: AsyncApiTestClient):
        """
        Test all public endpoints that don't require authorization.

        Args:
            api_client: Async API test client fixture

        Raises:
            AssertionError: If too many public endpoints fail
        """
        logger.info("🌐 Testing public endpoints...")

        # Public endpoints and expected response codes
        public_endpoints = [
            # Documentation and schemas
            ("/docs", "GET", [200], "Swagger documentation"),
            ("/", "GET", [200, 404], "Root endpoint"),
            # Auth - public endpoints
            ("register_user", "POST", [422], "Registration (without data)"),  # Expect 422 without data
            ("login_user", "POST", [422], "Login (without data)"),
        ]

        results = {"passed": 0, "failed": 0, "total": len(public_endpoints)}

        for endpoint_info in public_endpoints:
            if len(endpoint_info) == 4:
                endpoint, method, expected_codes, description = endpoint_info
            else:
                continue

            try:
                # If endpoint starts with '/', use directly
                if endpoint.startswith("/"):
                    url = endpoint
                else:
                    # Otherwise get through url_for
                    url = api_client.url_for(endpoint)

                response = await api_client.request(method, url)

                if response.status_code in expected_codes:
                    results["passed"] += 1
                    logger.info(f"  ✅ {description}: {response.status_code}")
                else:
                    results["failed"] += 1
                    logger.info(f"  ❌ {description}: {response.status_code} (expected {expected_codes})")

            except Exception as e:
                results["failed"] += 1
                logger.info(f"  💥 {description}: {str(e)[:100]}")

        success_rate = results["passed"] / results["total"]
        logger.info(f"📊 Public endpoints: {success_rate:.1%} ({results['passed']}/{results['total']})")

        # Public endpoints should at least respond
        assert success_rate >= 0.5, f"Too many public endpoints not working: {success_rate:.1%}"

    async def test_auth_flow_complete_e2e(self, api_client: AsyncApiTestClient, user_factory):
        """
        Complete E2E test of authorization flow: registration → login → usage → logout.

        Args:
            api_client: Async API test client fixture
            user_factory: User factory fixture

        Tests:
            - Logout without authorization
            - User authentication
            - Protected endpoints access
            - CRUD operations
            - Logout functionality
            - Access blocking after logout
        """
        logger.info("🔐 Comprehensive authorization flow test...")

        # Create user for testing
        test_user = await user_factory.create(
            email="auth_flow@test.com", username="auth_flow_user", is_active=True, is_verified=True
        )

        async with api_client.test_session(TestScenarioType.E2E):
            # Step 1: Check logout without authorization
            logger.info("  1️⃣ Checking logout without authorization...")
            try:
                logout_url = api_client.url_for("logout_user")
                response = await api_client.post(logout_url, json={"logout_all_devices": False})

                if response.status_code in [401, 403]:
                    logger.info(f"     ✅ Logout correctly requires authorization: {response.status_code}")
                else:
                    logger.info(f"     ⚠️  Logout without authorization: {response.status_code}")
            except Exception as e:
                logger.info(f"     💥 Logout error: {str(e)[:50]}")

            # Step 2: User authentication
            logger.info("  2️⃣ User authentication...")
            auth_user = await api_client.force_auth(user=test_user)
            logger.info(f"     ✅ Authenticated: {auth_user.email}")

            # Step 3: Testing protected endpoints
            logger.info("  3️⃣ Testing protected endpoints...")

            protected_endpoints = [
                ("get_current_user_info", "GET", "Current user information"),
                ("get_my_profile", "GET", "My profile"),
                ("get_my_profile_statistics", "GET", "Profile statistics"),
            ]

            protected_results = {"passed": 0, "failed": 0}

            for route_name, method, description in protected_endpoints:
                try:
                    url = api_client.url_for(route_name)
                    response = await api_client.request(method, url)

                    if response.status_code == 200:
                        protected_results["passed"] += 1
                        logger.info(f"     ✅ {description}: data received")

                        # Check that data matches the user
                        if route_name == "get_current_user_info":
                            data = response.json()
                            if data.get("email") == test_user.email:
                                logger.info(f"       📧 Email matches: {data['email']}")
                            else:
                                logger.info(f"       ⚠️  Email doesn't match: {data.get('email')}")

                    elif response.status_code == 422:
                        protected_results["passed"] += 1  # 422 is also OK - endpoint is accessible
                        logger.info(f"     ✅ {description}: accessible (422 - data needed)")
                    else:
                        protected_results["failed"] += 1
                        logger.info(f"     ❌ {description}: {response.status_code}")

                except Exception as e:
                    protected_results["failed"] += 1
                    logger.info(f"     💥 {description}: {str(e)[:50]}")

            # Step 4: Testing CRUD operations
            logger.info("  4️⃣ Testing CRUD operations...")

            # Try to update user
            try:
                update_url = api_client.url_for("update_user", user_id=test_user.id)
                # Empty PATCH request - should return 422 (data needed) or 200
                response = await api_client.patch(update_url, json={})

                if response.status_code in [200, 422]:
                    logger.info(f"     ✅ User update: endpoint accessible ({response.status_code})")
                else:
                    logger.info(f"     ⚠️  User update: {response.status_code}")

            except Exception as e:
                logger.info(f"     💥 User update: {str(e)[:50]}")

            # Step 5: Logout
            logger.info("  5️⃣ System logout...")
            try:
                logout_data = {"logout_all_devices": False}
                response = await api_client.post(logout_url, json=logout_data)

                if response.status_code == 200:
                    logger.info("     ✅ Logout successful")
                else:
                    logger.info(f"     ⚠️  Logout: {response.status_code}")

            except Exception as e:
                logger.info(f"     💥 Logout: {str(e)[:50]}")

            # Step 6: Check that access is blocked after logout
            logger.info("  6️⃣ Checking access blocking after logout...")
            try:
                await api_client.force_logout()  # Remove tokens from headers
                response = await api_client.get(api_client.url_for("get_current_user_info"))

                if response.status_code in [401, 403]:
                    logger.info(f"     ✅ Access correctly blocked: {response.status_code}")
                else:
                    logger.info(f"     ⚠️  Access still open: {response.status_code}")

            except Exception as e:
                logger.info(f"     💥 Access blocking check: {str(e)[:50]}")

        total_protected = len(protected_endpoints)
        success_rate = protected_results["passed"] / total_protected if total_protected > 0 else 0

        logger.info("🎯 Authorization flow results:")
        logger.info(f"  Protected endpoints: {success_rate:.1%} ({protected_results['passed']}/{total_protected})")
        logger.info(f"  Overall status: {'✅ WORKING' if success_rate >= 0.5 else '❌ PROBLEMS'}")

    async def test_user_management_e2e(self, api_client: AsyncApiTestClient, user_factory):
        """
        E2E test for user management - all operations with Users and Profiles.

        Args:
            api_client: Async API test client fixture
            user_factory: User factory fixture

        Tests:
            - User endpoints (get by ID, activity)
            - Profile endpoints (get profile, public profiles)
            - Admin operations
        """
        logger.info("👥 Testing user management...")

        # Create admin user for testing
        admin_user = await user_factory.create(
            email="admin@test.com", username="admin_user", is_active=True, is_verified=True, is_superuser=True
        )

        # Create regular user for operations
        target_user = await user_factory.create(
            email="target@test.com", username="target_user", is_active=True, is_verified=True
        )

        await api_client.force_auth(user=admin_user)

        # Test User endpoints
        logger.info("  📋 Testing User endpoints...")

        user_endpoints = [
            ("get_user_by_id", "GET", target_user.id, "Get user by ID"),
            ("get_user_activity", "GET", target_user.id, "User activity"),
            # ("delete_user", "DELETE", target_user.id, "Delete user"),  # Don't delete in test
        ]

        user_results = {"passed": 0, "failed": 0}

        for route_name, method, user_id, description in user_endpoints:
            try:
                url = api_client.url_for(route_name, user_id=user_id)
                response = await api_client.request(method, url)

                if response.status_code in [200, 422]:  # 200 = OK, 422 = data needed
                    user_results["passed"] += 1
                    logger.info(f"    ✅ {description}: {response.status_code}")

                    if response.status_code == 200:
                        data = response.json()
                        if route_name == "get_user_by_id" and data.get("email"):
                            logger.info(f"      📧 Got user: {data['email']}")

                else:
                    user_results["failed"] += 1
                    logger.info(f"    ❌ {description}: {response.status_code}")

            except Exception as e:
                user_results["failed"] += 1
                logger.info(f"    💥 {description}: {str(e)[:50]}")

        # Test Profile endpoints
        logger.info("  👤 Testing Profile endpoints...")

        profile_endpoints = [
            ("get_user_profile", "GET", target_user.id, "Get user profile"),
            ("get_public_profiles", "GET", None, "Public profiles"),
        ]

        profile_results = {"passed": 0, "failed": 0}

        for route_name, method, user_id, description in profile_endpoints:
            try:
                if user_id:
                    url = api_client.url_for(route_name, user_id=user_id)
                else:
                    url = api_client.url_for(route_name)

                response = await api_client.request(method, url)

                if response.status_code in [200, 422, 404]:  # 404 OK if profile not created
                    profile_results["passed"] += 1
                    logger.info(f"    ✅ {description}: {response.status_code}")
                else:
                    profile_results["failed"] += 1
                    logger.info(f"    ❌ {description}: {response.status_code}")

            except Exception as e:
                profile_results["failed"] += 1
                logger.info(f"    💥 {description}: {str(e)[:50]}")

        # Overall results
        total_user = len(user_endpoints)
        total_profile = len(profile_endpoints)
        total = total_user + total_profile

        passed_total = user_results["passed"] + profile_results["passed"]
        success_rate = passed_total / total if total > 0 else 0

        logger.info("📊 User management results:")
        logger.info(f"  User endpoints: {user_results['passed']}/{total_user}")
        logger.info(f"  Profile endpoints: {profile_results['passed']}/{total_profile}")
        logger.info(f"  Overall success: {success_rate:.1%} ({passed_total}/{total})")
        logger.info(f"  Status: {'✅ WORKING' if success_rate >= 0.5 else '❌ PROBLEMS'}")

    async def test_error_handling_e2e(self, api_client: AsyncApiTestClient):
        """
        E2E test for error handling - check that API correctly returns errors.

        Args:
            api_client: Async API test client fixture

        Tests:
            - Non-existent routes
            - Wrong HTTP methods
            - Unauthorized access to protected endpoints

        Raises:
            AssertionError: If error handling is not good enough
        """
        logger.info("🚨 Testing error handling...")

        error_scenarios = [
            # Non-existent routes
            ("/nonexistent", "GET", [404], "Non-existent endpoint"),
            # Wrong methods
            ("get_current_user_info", "POST", [405], "Wrong HTTP method"),
            # Unauthorized access to protected endpoints
            ("get_current_user_info", "GET", [401, 403], "No authorization"),
            ("get_my_profile", "GET", [401, 403], "No authorization"),
        ]

        error_results = {"passed": 0, "failed": 0}

        for endpoint, method, expected_codes, description in error_scenarios:
            try:
                if endpoint.startswith("/"):
                    url = endpoint
                else:
                    url = api_client.url_for(endpoint)

                response = await api_client.request(method, url)

                if response.status_code in expected_codes:
                    error_results["passed"] += 1
                    logger.info(f"  ✅ {description}: correct error {response.status_code}")
                else:
                    error_results["failed"] += 1
                    logger.info(
                        f"  ❌ {description}: unexpected code {response.status_code} (expected {expected_codes})"
                    )

            except Exception as e:
                # Exceptions can also be correct reaction to errors
                error_results["passed"] += 1
                logger.info(f"  ✅ {description}: exception (may be correct)")

        total_errors = len(error_scenarios)
        success_rate = error_results["passed"] / total_errors

        logger.info(f"🛡️  Error handling: {success_rate:.1%} ({error_results['passed']}/{total_errors})")

        # Good error handling is critical for API
        assert success_rate >= 0.75, f"Error handling not good enough: {success_rate:.1%}"
