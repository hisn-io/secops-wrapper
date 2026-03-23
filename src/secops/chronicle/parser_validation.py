# Copyright 2026 Google LLC
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
"""Chronicle parser validation functionality."""

from typing import TYPE_CHECKING, Any
import logging
import re

from secops.exceptions import APIError, SecOpsError

if TYPE_CHECKING:
    from secops.chronicle.client import ChronicleClient


def trigger_github_checks(
    client: "ChronicleClient",
    associated_pr: str,
    log_type: str,
    customer_id: str | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    """Trigger GitHub checks for a parser.

    Args:
        client: ChronicleClient instance
        associated_pr: The PR string (e.g., "owner/repo/pull/123").
        log_type: The string name of the LogType enum.
        customer_id: Optional. The customer UUID string. Defaults to client
            configured ID.
        timeout: Optional RPC timeout in seconds (default: 60).

    Returns:
        Dictionary containing the response details.

    Raises:
        SecOpsError: If input is invalid.
        APIError: If the API request fails.
    """
    if not isinstance(log_type, str) or len(log_type.strip()) < 2:
        raise SecOpsError("log_type must be a valid string of length >= 2")
    if customer_id is not None:
        if not isinstance(customer_id, str) or not re.match(
            r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
            r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
            customer_id,
        ):
            raise SecOpsError(
                "customer_id must be a valid UUID string"
            )
    if not isinstance(associated_pr, str) or not associated_pr.strip():
        raise SecOpsError("associated_pr must be a non-empty string")

    pr_parts = associated_pr.split("/")
    if len(pr_parts) != 4 or pr_parts[2] != "pull" or not pr_parts[3].isdigit():
        raise SecOpsError(
            "associated_pr must be in the format 'owner/repo/pull/<number>'"
        )
    if not isinstance(timeout, int) or timeout < 0:
        raise SecOpsError("timeout must be a non-negative integer")

    eff_customer_id = customer_id or client.customer_id
    instance_id = client.instance_id
    if eff_customer_id and eff_customer_id != client.customer_id:
        # Dev and staging use 'us' as the location
        region = "us" if client.region in ["dev", "staging"] else client.region
        instance_id = (
            f"projects/{client.project_id}/locations/"
            f"{region}/instances/{eff_customer_id}"
        )

    # The backend expects the resource name to be in the format:
    # projects/*/locations/*/instances/*/logTypes/*/parsers/<UUID>
    base_url = client.base_url(version="v1alpha")

    # First get the list of parsers for this log_type to find a valid
    # parser UUID
    parsers_url = f"{base_url}/{instance_id}/logTypes/{log_type}/parsers"
    parsers_resp = client.session.get(parsers_url, timeout=timeout)
    if not parsers_resp.ok:
        raise APIError(
            f"Failed to fetch parsers for log type {log_type}: "
            f"{parsers_resp.text}"
        )

    parsers_data = parsers_resp.json()
    parsers = parsers_data.get("parsers")
    if not parsers:
        logging.info(
            "No parsers found for log type %s. Using fallback parser ID.",
            log_type,
        )
        parser_name = f"{instance_id}/logTypes/{log_type}/parsers/-"
    else:
        if len(parsers) > 1:
            logging.warning(
                "Multiple parsers found for log type %s. Using the first one.",
                log_type,
            )

        # Use the first parser's name (which includes the UUID)
        parser_name = parsers[0]["name"]

    url = f"{base_url}/{parser_name}:runAnalysis"
    payload = {
        "report_type": "GITHUB_PARSER_VALIDATION",
        "pull_request": associated_pr,
    }

    response = client.session.post(url, json=payload, timeout=timeout)

    if not response.ok:
        raise APIError(f"API call failed: {response.text}")

    return response.json()


def get_analysis_report(
    client: "ChronicleClient",
    name: str,
    timeout: int = 60,
) -> dict[str, Any]:
    """Get a parser analysis report.
    Args:
        client: ChronicleClient instance
        name: The full resource name of the analysis report.
        timeout: Optional timeout in seconds (default: 60).
    Returns:
        Dictionary containing the analysis report.
    Raises:
        SecOpsError: If input is invalid.
        APIError: If the API request fails.
    """
    if not isinstance(name, str) or len(name.strip()) < 5:
        raise SecOpsError("name must be a valid string")
    if not isinstance(timeout, int) or timeout < 0:
        raise SecOpsError("timeout must be a non-negative integer")

    # The name includes 'projects/...', so we just append it to base_url
    base_url = client.base_url(version="v1alpha")
    url = f"{base_url}/{name}"

    response = client.session.get(url, timeout=timeout)

    if not response.ok:
        raise APIError(f"API call failed: {response.text}")

    return response.json()
