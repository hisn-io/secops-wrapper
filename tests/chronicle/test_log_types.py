# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Tests for Chronicle log types functionality."""

from unittest.mock import Mock

import pytest

from secops.chronicle import log_types
from secops.chronicle.log_types import (
    LogType,
    get_all_log_types,
    get_log_type_description,
    is_valid_log_type,
    load_log_types,
    search_log_types,
)


@pytest.fixture
def mock_chronicle_client():
    """Create a mock Chronicle client."""
    client = Mock()
    client.base_url = "https://us-chronicle.googleapis.com/v1alpha"
    client.instance_id = "projects/123/locations/us/instances/456"
    client.session = Mock()
    return client


@pytest.fixture
def mock_api_response():
    """Create a mock API response with log types."""
    return {
        "logTypes": [
            {
                "name": (
                    "projects/123/locations/us/instances/456/logTypes/OKTA"
                ),
                "displayName": "Okta Identity Management",
            },
            {
                "name": (
                    "projects/123/locations/us/instances/456/logTypes/AWS_CLOUDTRAIL"  # pylint: disable=line-too-long
                ),
                "displayName": "AWS Cloudtrail",
            },
            {
                "name": (
                    "projects/123/locations/us/instances/456/logTypes/WINDOWS"  # pylint: disable=line-too-long
                ),
                "displayName": "Windows Event Logs",
            },
        ]
    }


@pytest.fixture
def mock_api_response_paginated_page1():
    """Create a mock API response for first page."""
    return {
        "logTypes": [
            {
                "name": (
                    "projects/123/locations/us/instances/456/logTypes/OKTA"
                ),
                "displayName": "Okta",
            },
            {
                "name": (
                    "projects/123/locations/us/instances/456/logTypes/AWS_CLOUDTRAIL"  # pylint: disable=line-too-long
                ),
                "displayName": "AWS Cloudtrail",
            },
        ],
        "nextPageToken": "page2_token",
    }


@pytest.fixture
def mock_api_response_paginated_page2():
    """Create a mock API response for second page."""
    return {
        "logTypes": [
            {
                "name": (
                    "projects/123/locations/us/instances/456/logTypes/WINDOWS"  # pylint: disable=line-too-long
                ),
                "displayName": "Windows Event Logs",
            },
        ]
    }


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset cache before each test."""
    # pylint: disable=protected-access
    log_types._LOG_TYPES_CACHE = None
    yield
    # Clean up after test
    log_types._LOG_TYPES_CACHE = None


def test_load_log_types_static():
    """Test loading log types from static data."""
    result = load_log_types(force_static=True)

    assert isinstance(result, dict)
    assert len(result) > 0
    # Check some known log types
    assert "OKTA" in result
    assert "AWS_CLOUDTRAIL" in result
    assert isinstance(result["OKTA"], LogType)
    assert result["OKTA"].id == "OKTA"


def test_load_log_types_from_api(mock_chronicle_client, mock_api_response):
    """Test loading log types from API (fetches all pages by default)."""
    # Mock the API response (no nextPageToken = single page)
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_api_response
    mock_chronicle_client.session.get.return_value = mock_response

    result = load_log_types(client=mock_chronicle_client)

    assert isinstance(result, dict)
    assert "OKTA" in result
    assert "AWS_CLOUDTRAIL" in result
    assert "WINDOWS" in result
    assert result["OKTA"].description == "Okta Identity Management"
    # Verify pagination params: pageSize=1000 for fetching all
    call_args = mock_chronicle_client.session.get.call_args
    assert call_args[1]["params"]["pageSize"] == 1000


def test_load_log_types_api_pagination(
    mock_chronicle_client,
    mock_api_response_paginated_page1,
    mock_api_response_paginated_page2,
):
    """Test loading log types from API with pagination (all pages)."""
    # Mock the API responses for pagination
    mock_response_page1 = Mock()
    mock_response_page1.status_code = 200
    mock_response_page1.json.return_value = mock_api_response_paginated_page1

    mock_response_page2 = Mock()
    mock_response_page2.status_code = 200
    mock_response_page2.json.return_value = mock_api_response_paginated_page2

    mock_chronicle_client.session.get.side_effect = [
        mock_response_page1,
        mock_response_page2,
    ]

    result = load_log_types(client=mock_chronicle_client)

    # Verify pagination worked - should fetch all pages
    assert len(result) == 3
    assert "OKTA" in result
    assert "AWS_CLOUDTRAIL" in result
    assert "WINDOWS" in result
    # Verify get was called twice (once per page)
    assert mock_chronicle_client.session.get.call_count == 2


def test_fetch_log_types_single_page(
    mock_chronicle_client, mock_api_response_paginated_page1
):
    """Test fetching single page when page_size is specified."""
    from secops.chronicle.log_types import _fetch_log_types_from_api

    # Mock API response with nextPageToken (more data available)
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_api_response_paginated_page1
    mock_chronicle_client.session.get.return_value = mock_response

    # Fetch with explicit page_size - should fetch only one page
    result = _fetch_log_types_from_api(
        client=mock_chronicle_client, page_size=2
    )

    # Should return only first page results, not continue pagination
    assert len(result) == 2
    assert "OKTA" in result
    assert "AWS_CLOUDTRAIL" in result
    # Verify get was called only once
    assert mock_chronicle_client.session.get.call_count == 1
    # Verify correct page_size was used
    call_args = mock_chronicle_client.session.get.call_args
    assert call_args[1]["params"]["pageSize"] == 2


def test_fetch_log_types_with_page_token(
    mock_chronicle_client, mock_api_response_paginated_page2
):
    """Test fetching with page_token parameter."""
    from secops.chronicle.log_types import _fetch_log_types_from_api

    # Mock API response for second page
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_api_response_paginated_page2
    mock_chronicle_client.session.get.return_value = mock_response

    # Fetch with page_token
    result = _fetch_log_types_from_api(
        client=mock_chronicle_client,
        page_size=10,
        page_token="page2_token",
    )

    # Should have results from second page
    assert "WINDOWS" in result
    # Verify page_token was passed
    call_args = mock_chronicle_client.session.get.call_args
    assert call_args[1]["params"]["pageToken"] == "page2_token"
    assert call_args[1]["params"]["pageSize"] == 10


def test_load_log_types_api_fallback(mock_chronicle_client):
    """Test fallback to static data when API fails."""
    # Mock API failure
    mock_chronicle_client.session.get.side_effect = Exception("API Error")

    result = load_log_types(client=mock_chronicle_client)

    # Should fall back to static data
    assert isinstance(result, dict)
    assert len(result) > 0
    # Check for static log types
    assert "OKTA" in result


def test_load_log_types_no_client():
    """Test loading log types without client (should use static)."""
    result = load_log_types(client=None)

    assert isinstance(result, dict)
    assert len(result) > 0


def test_load_log_types_cache():
    """Test that log types are cached."""
    # First call - should load
    result1 = load_log_types(force_static=True)

    # Second call - should return cached data
    result2 = load_log_types(force_static=True)

    # Should be the same object (cached)
    assert result1 is result2


def test_get_all_log_types_static():
    """Test getting all log types from static data."""
    result = get_all_log_types(force_static=True)

    assert isinstance(result, list)
    assert len(result) > 0
    assert all(isinstance(lt, LogType) for lt in result)


def test_get_all_log_types_from_api(mock_chronicle_client, mock_api_response):
    """Test getting all log types from API."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_api_response
    mock_chronicle_client.session.get.return_value = mock_response

    result = get_all_log_types(client=mock_chronicle_client)

    assert isinstance(result, list)
    assert len(result) == 3


def test_is_valid_log_type_static():
    """Test validating log type from static data."""
    assert is_valid_log_type("OKTA", force_static=True)
    assert is_valid_log_type("AWS_CLOUDTRAIL", force_static=True)
    assert not is_valid_log_type("INVALID_TYPE", force_static=True)


def test_is_valid_log_type_from_api(mock_chronicle_client, mock_api_response):
    """Test validating log type from API."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_api_response
    mock_chronicle_client.session.get.return_value = mock_response

    assert is_valid_log_type("OKTA", client=mock_chronicle_client)
    assert is_valid_log_type("AWS_CLOUDTRAIL", client=mock_chronicle_client)


def test_get_log_type_description_static():
    """Test getting log type description from static data."""
    desc = get_log_type_description("OKTA", force_static=True)
    assert desc is not None
    assert isinstance(desc, str)

    # Non-existent log type
    assert get_log_type_description("INVALID_TYPE", force_static=True) is None


def test_get_log_type_description_from_api(
    mock_chronicle_client, mock_api_response
):
    """Test getting log type description from API."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_api_response
    mock_chronicle_client.session.get.return_value = mock_response

    desc = get_log_type_description("OKTA", client=mock_chronicle_client)
    assert desc == "Okta Identity Management"


def test_search_log_types_static():
    """Test searching log types from static data."""
    # Search by ID
    results = search_log_types("OKTA", force_static=True)
    assert len(results) > 0
    assert any(lt.id == "OKTA" for lt in results)

    # Search by description (case insensitive)
    results = search_log_types("windows", force_static=True)
    assert len(results) > 0


def test_search_log_types_from_api(mock_chronicle_client, mock_api_response):
    """Test searching log types from API."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_api_response
    mock_chronicle_client.session.get.return_value = mock_response

    results = search_log_types("OKTA", client=mock_chronicle_client)
    assert len(results) >= 1
    assert any(lt.id == "OKTA" for lt in results)


def test_search_log_types_case_sensitive(mock_chronicle_client):
    """Test case-sensitive search."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "logTypes": [
            {
                "name": "projects/123/locations/us/instances/456/logTypes/OKTA",  # pylint: disable=line-too-long
                "displayName": "Okta",
            }
        ]
    }
    mock_chronicle_client.session.get.return_value = mock_response

    # Case sensitive - should find
    results = search_log_types(
        "OKTA", case_sensitive=True, client=mock_chronicle_client
    )
    assert len(results) >= 1

    # Clear cache between searches to ensure fresh data
    # pylint: disable=protected-access
    log_types._LOG_TYPES_CACHE = None

    # Case sensitive - should not find
    results = search_log_types(
        "okta", case_sensitive=True, client=mock_chronicle_client
    )
    assert len(results) == 0


def test_search_log_types_id_only(mock_chronicle_client):
    """Test searching only in log type IDs."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "logTypes": [
            {
                "name": "projects/123/locations/us/instances/456/logTypes/OKTA",  # pylint: disable=line-too-long
                "displayName": "Okta Identity Management",
            }
        ]
    }
    mock_chronicle_client.session.get.return_value = mock_response

    # Search in ID only
    results = search_log_types(
        "OKTA",
        search_in_description=False,
        client=mock_chronicle_client,
    )
    assert len(results) >= 1

    # Clear cache between searches to ensure fresh data
    # pylint: disable=protected-access
    log_types._LOG_TYPES_CACHE = None

    # Search for description term (should not find)
    results = search_log_types(
        "Identity",
        search_in_description=False,
        client=mock_chronicle_client,
    )
    assert len(results) == 0


def test_api_response_missing_fields(mock_chronicle_client):
    """Test handling API response with missing fields."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "logTypes": [
            {
                # Missing name field
                "displayName": "Test Log Type",
            },
            {
                "name": "projects/123/locations/us/instances/456/logTypes/OKTA",  # pylint: disable=line-too-long
                # Missing displayName - should use ID
            },
        ]
    }
    mock_chronicle_client.session.get.return_value = mock_response

    result = load_log_types(client=mock_chronicle_client)

    # Should handle gracefully - OKTA should be present
    assert "OKTA" in result
