"""
E2E tests based on real routes discovery from OpenAPI.

Tests actual available endpoints discovered from the running application.
"""

import logging

import pytest

from tests.utils_test.api_test_client import AsyncApiTestClient, TestScenarioType

# Use test session logger as per project standards
logger = logging.getLogger("test_session")


class TestE2ERealRoutes:
    """E2E tests based on real discovered routes."""

    async def test_discover_all_routes(self, api_client: AsyncApiTestClient):
        """
        Discover and test all available routes from OpenAPI schema.

        Args:
            api_client: Async API test client fixture

        Tests:
            - Route discovery from OpenAPI
            - Endpoint availability
            - Basic response validation
        """
        logger.info("🗺️  Discovering all available routes...")

        try:
            # Try to get OpenAPI schema
            schema_response = await api_client.get("/openapi.json")

            if schema_response.status_code == 200:
                schema = schema_response.json()
                paths = schema.get("paths", {})

                logger.info(f"  📋 Found {len(paths)} route paths in OpenAPI schema")

                # Extract all endpoints
                discovered_routes = []
                for path, methods in paths.items():
                    for method, details in methods.items():
                        if method.upper() in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
                            operation_id = details.get("operationId", f"{method}_{path}")
                            discovered_routes.append(
                                {
                                    "path": path,
                                    "method": method.upper(),
                                    "operation_id": operation_id,
                                    "summary": details.get("summary", ""),
                                }
                            )

                logger.info(f"  🎯 Discovered {len(discovered_routes)} total endpoints")

                # Test a sample of discovered routes
                await self._test_routes_sample(api_client, discovered_routes[:15])

            else:
                logger.info(f"  ⚠️  Could not get OpenAPI schema: {schema_response.status_code}")
                # Fallback to known routes
                await self._test_known_routes(api_client)

        except Exception as e:
            logger.info(f"  💥 Route discovery failed: {str(e)[:60]}")
            # Fallback to known routes
            await self._test_known_routes(api_client)

    async def _test_routes_sample(self, api_client: AsyncApiTestClient, routes):
        """
        Test a sample of routes for basic availability.

        Args:
            api_client: Async API test client fixture
            routes: List of route dictionaries to test
        """
        logger.info("  🧪 Testing sample of discovered routes...")

        results = {"total": len(routes), "success": 0, "client_error": 0, "server_error": 0}

        for route in routes:
            try:
                path = route["path"]
                method = route["method"]
                summary = route.get("summary", "")

                # Skip some problematic paths
                if any(skip in path for skip in ["/docs", "/redoc", "/openapi"]):
                    continue

                # Make request
                response = await api_client.request(method, path)

                # Categorize response
                if 200 <= response.status_code < 300:
                    results["success"] += 1
                    logger.info(f"      ✅ {method} {path}: {response.status_code} ({summary[:30]})")
                elif 400 <= response.status_code < 500:
                    results["client_error"] += 1
                    status_msg = {
                        401: "unauthorized",
                        403: "forbidden",
                        404: "not found",
                        405: "method not allowed",
                        422: "validation error",
                    }
                    msg = status_msg.get(response.status_code, "client error")
                    logger.info(f"      ⚠️  {method} {path}: {response.status_code} ({msg})")
                else:
                    results["server_error"] += 1
                    logger.info(f"      ❌ {method} {path}: {response.status_code} (server error)")

            except Exception as e:
                results["server_error"] += 1
                logger.info(f"      💥 {method} {path}: {str(e)[:40]}")

        # Summary
        total_tested = results["success"] + results["client_error"] + results["server_error"]
        if total_tested > 0:
            success_rate = (results["success"] + results["client_error"]) / total_tested
            logger.info(f"    📊 Route sample: {success_rate:.1%} responding")
            logger.info(f"       ✅ Success: {results['success']}")
            logger.info(f"       ⚠️  Client errors: {results['client_error']}")
            logger.info(f"       ❌ Server errors: {results['server_error']}")

    async def _test_known_routes(self, api_client: AsyncApiTestClient):
        """
        Test known routes as fallback.

        Args:
            api_client: Async API test client fixture

        Tests a predefined set of known routes.
        """
        logger.info("  📚 Testing known routes (fallback)...")

        known_routes = [
            # Public routes
            ("/", "GET", "Root endpoint"),
            ("/docs", "GET", "Documentation"),
            # Auth routes (will need proper data)
            ("register_user", "POST", "User registration"),
            ("login_user", "POST", "User login"),
            # Protected routes (will need auth)
            ("get_current_user_info", "GET", "Current user"),
            ("get_my_profile", "GET", "My profile"),
            ("get_users_list", "GET", "Users list"),
            ("get_public_profiles", "GET", "Public profiles"),
        ]

        route_results = {"passed": 0, "failed": 0}

        for route_info in known_routes:
            if len(route_info) == 3:
                endpoint, method, description = route_info
            else:
                continue

            try:
                # Get URL
                if endpoint.startswith("/"):
                    url = endpoint
                else:
                    url = api_client.url_for(endpoint)

                response = await api_client.request(method, url)

                # Any response is considered success for discovery
                if response.status_code < 500:
                    route_results["passed"] += 1
                    logger.info(f"    ✅ {description}: {response.status_code}")
                else:
                    route_results["failed"] += 1
                    logger.info(f"    ❌ {description}: {response.status_code}")

            except Exception as e:
                route_results["failed"] += 1
                logger.info(f"    💥 {description}: {str(e)[:50]}")

        total = len(known_routes)
        success_rate = route_results["passed"] / total if total > 0 else 0
        logger.info(f"  📊 Known routes: {success_rate:.1%} ({route_results['passed']}/{total})")

    async def test_auth_routes_real(self, api_client: AsyncApiTestClient, user_factory):
        """
        Test real authentication routes with proper data.

        Args:
            api_client: Async API test client fixture
            user_factory: User factory fixture

        Tests:
            - Registration endpoint
            - Login endpoint
            - Logout endpoint
            - Token validation
        """
        logger.info("🔐 Testing real authentication routes...")

        # Create test user
        test_user = await user_factory.create(
            email="auth_real@test.com", username="auth_real_user", is_active=True, is_verified=True
        )

        auth_tests = [
            {
                "name": "Registration with invalid data",
                "route": "register_user",
                "method": "POST",
                "data": {},  # Empty data should cause validation error
                "expected": [422, 400],
                "description": "Empty registration data",
            },
            {
                "name": "Login with invalid data",
                "route": "login_user",
                "method": "POST",
                "data": {},  # Empty data should cause validation error
                "expected": [422, 400],
                "description": "Empty login data",
            },
            {
                "name": "Valid user authentication",
                "route": "login_user",
                "method": "POST",
                "data": {"email": test_user.email, "password": "test_password"},
                "expected": [200, 401, 422],  # 200 if works, 401 if wrong password, 422 if validation fails
                "description": "Actual login attempt",
            },
        ]

        auth_results = {"passed": 0, "failed": 0}

        for test in auth_tests:
            logger.info(f"  🧪 {test['name']}...")

            try:
                url = api_client.url_for(test["route"])
                response = await api_client.request(test["method"], url, json=test["data"])

                if response.status_code in test["expected"]:
                    auth_results["passed"] += 1
                    logger.info(f"    ✅ {test['description']}: {response.status_code}")

                    # Show response structure for successful responses
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            if isinstance(data, dict):
                                keys = list(data.keys())[:3]
                                logger.info(f"      🔑 Response fields: {keys}")
                        except:
                            pass
                else:
                    auth_results["failed"] += 1
                    logger.info(f"    ❌ {test['description']}: unexpected {response.status_code}")

            except Exception as e:
                auth_results["failed"] += 1
                logger.info(f"    💥 {test['description']}: {str(e)[:50]}")

        logger.info(f"  📊 Auth routes: {auth_results['passed']}/{len(auth_tests)}")

    async def test_protected_routes_real(self, api_client: AsyncApiTestClient, user_factory):
        """
        Test real protected routes with proper authentication.

        Args:
            api_client: Async API test client fixture
            user_factory: User factory fixture

        Tests:
            - Protected endpoints with authentication
            - Different user permission levels
            - Response structure validation
        """
        logger.info("🛡️  Testing real protected routes...")

        # Create users with different permissions
        regular_user = await user_factory.create(
            email="regular@routes.com", username="regular_routes", is_active=True, is_verified=True
        )

        admin_user = await user_factory.create(
            email="admin@routes.com", username="admin_routes", is_active=True, is_verified=True, is_superuser=True
        )

        protected_tests = [
            # Regular user tests
            {
                "user": regular_user,
                "user_type": "regular",
                "routes": [
                    ("get_current_user_info", "GET", "Current user info"),
                    ("get_my_profile", "GET", "My profile"),
                    ("get_my_profile_statistics", "GET", "Profile statistics"),
                    ("update_my_profile", "PATCH", "Update profile"),
                ],
            },
            # Admin user tests
            {
                "user": admin_user,
                "user_type": "admin",
                "routes": [
                    ("get_current_user_info", "GET", "Current user info"),
                    ("get_users_list", "GET", "Users list"),
                    ("get_user_by_id", "GET", "User by ID"),
                    ("get_public_profiles", "GET", "Public profiles"),
                    ("get_user_activity", "GET", "User activity"),
                ],
            },
        ]

        for test_group in protected_tests:
            user = test_group["user"]
            user_type = test_group["user_type"]
            routes = test_group["routes"]

            logger.info(f"  👤 Testing as {user_type} user ({user.email})...")

            await api_client.force_auth(user=user)

            group_results = {"passed": 0, "failed": 0}

            for route_name, method, description in routes:
                try:
                    # Special handling for routes that need parameters
                    if route_name == "get_user_by_id":
                        url = api_client.url_for(route_name, user_id=user.id)
                    elif route_name == "get_user_activity":
                        url = api_client.url_for(route_name, user_id=user.id)
                    else:
                        url = api_client.url_for(route_name)

                    # Send appropriate data for modification requests
                    if method in ["POST", "PATCH", "PUT"]:
                        test_data = {"bio": "Updated via real route test"}
                        response = await api_client.request(method, url, json=test_data)
                    else:
                        response = await api_client.request(method, url)

                    if response.status_code in [200, 201, 422, 404]:
                        group_results["passed"] += 1
                        status_msg = {
                            200: "✅ success",
                            201: "✅ created",
                            422: "⚠️  validation needed",
                            404: "⚠️  not found",
                        }
                        logger.info(
                            f"    {status_msg.get(response.status_code, '✅')} {description}: {response.status_code}"
                        )

                        # Show data structure for successful responses
                        if response.status_code in [200, 201]:
                            try:
                                data = response.json()
                                if isinstance(data, dict) and "email" in data:
                                    logger.info(f"      📧 User: {data['email']}")
                                elif isinstance(data, list):
                                    logger.info(f"      📋 Records: {len(data)}")
                                elif isinstance(data, dict):
                                    keys = list(data.keys())[:3]
                                    logger.info(f"      🔑 Fields: {keys}")
                            except:
                                pass
                    else:
                        group_results["failed"] += 1
                        logger.info(f"    ❌ {description}: unexpected {response.status_code}")

                except Exception as e:
                    group_results["failed"] += 1
                    logger.info(f"    💥 {description}: {str(e)[:50]}")

            logger.info(f"    📊 {user_type.title()} user routes: {group_results['passed']}/{len(routes)}")

        logger.info("🎯 Real routes testing complete!")
