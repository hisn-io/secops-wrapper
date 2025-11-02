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
"""Google SecOps CLI config commands"""

from secops.cli.constants import CONFIG_FILE
from secops.cli.utils.config_utils import load_config, save_config


def setup_config_command(subparsers):
    """Set up the config command parser.

    Args:
        subparsers: Subparsers object to add to
    """
    config_parser = subparsers.add_parser(
        "config", help="Manage CLI configuration"
    )
    config_subparsers = config_parser.add_subparsers(
        help="Config command", required=True
    )

    # Set config command
    set_parser = config_subparsers.add_parser(
        "set", help="Set configuration values"
    )
    set_parser.add_argument(
        "--customer-id",
        "--customer_id",
        dest="customer_id",
        help="Chronicle instance ID",
    )
    set_parser.add_argument(
        "--project-id", "--project_id", dest="project_id", help="GCP project ID"
    )
    set_parser.add_argument("--region", help="Chronicle API region")
    set_parser.add_argument(
        "--service-account",
        "--service_account",
        dest="service_account",
        help="Path to service account JSON file",
    )
    set_parser.add_argument(
        "--start-time",
        "--start_time",
        dest="start_time",
        help="Default start time in ISO format (YYYY-MM-DDTHH:MM:SSZ)",
    )
    set_parser.add_argument(
        "--end-time",
        "--end_time",
        dest="end_time",
        help="Default end time in ISO format (YYYY-MM-DDTHH:MM:SSZ)",
    )
    set_parser.add_argument(
        "--time-window",
        "--time_window",
        dest="time_window",
        type=int,
        help="Default time window in hours",
    )
    set_parser.set_defaults(func=handle_config_set_command)

    # View config command
    view_parser = config_subparsers.add_parser(
        "view", help="View current configuration"
    )
    view_parser.set_defaults(func=handle_config_view_command)

    # Clear config command
    clear_parser = config_subparsers.add_parser(
        "clear", help="Clear current configuration"
    )
    clear_parser.set_defaults(func=handle_config_clear_command)


def handle_config_set_command(args, chronicle=None):
    """Handle config set command.

    Args:
        args: Command line arguments
        chronicle: Not used for this command
    """
    config = load_config()

    # Update config with new values
    if args.customer_id:
        config["customer_id"] = args.customer_id
    if args.project_id:
        config["project_id"] = args.project_id
    if args.region:
        config["region"] = args.region
    if args.service_account:
        config["service_account"] = args.service_account
    if args.start_time:
        config["start_time"] = args.start_time
    if args.end_time:
        config["end_time"] = args.end_time
    if args.time_window is not None:
        config["time_window"] = args.time_window

    save_config(config)
    print(f"Configuration saved to {CONFIG_FILE}")

    # Unused argument
    _ = (chronicle,)


def handle_config_view_command(args, chronicle=None):
    """Handle config view command.

    Args:
        args: Command line arguments
        chronicle: Not used for this command
    """
    config = load_config()

    if not config:
        print("No configuration found.")
        return

    print("Current configuration:")
    for key, value in config.items():
        print(f"  {key}: {value}")

    # Unused arguments
    _ = (args, chronicle)


def handle_config_clear_command(args, chronicle=None):
    """Handle config clear command.

    Args:
        args: Command line arguments
        chronicle: Not used for this command
    """
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()
        print("Configuration cleared.")
    else:
        print("No configuration found.")

    # Unused arguments
    _ = (args, chronicle)
