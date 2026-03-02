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
"""Formatting helper functions for Chronicle."""

from typing import Any

def build_patch_body(
    field_map: list[tuple[str, str, Any]],
    update_mask: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Build a request body and params dict for a PATCH request.

    Args:
        field_map: List of (api_key, mask_key, value) tuples for
            each optional field.
        update_mask: Explicit update mask. If provided,
            overrides the auto-generated mask.

    Returns:
        Tuple of (body, params) where params contains the updateMask or is None.
    """
    body = {api_key: value for api_key, _, value in field_map if value is not None}
    mask_fields = [mask_key for _, mask_key, value in field_map if value is not None]

    resolved_mask = update_mask or (",".join(mask_fields) if mask_fields else None)
    params = {"updateMask": resolved_mask} if resolved_mask else None

    return body, params