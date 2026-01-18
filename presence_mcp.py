import logging
from typing import List
from datetime import datetime, timezone
from mcplib.server import MCPServer
from presence import Presence

def _get_duration_str(last_change: datetime) -> str:
    """
    Calculates a human-readable duration string since the last state change.
    Ensures both datetimes are offset-aware to prevent TypeErrors.
    """
    if not last_change:
        return "unknown duration"

    # 1. Get current time in UTC (offset-aware)
    now = datetime.now(timezone.utc)

    # 2. Handle potential offset-naive datetimes from the source
    if last_change.tzinfo is None:
        # Assume UTC if no timezone info is present
        last_change = last_change.replace(tzinfo=timezone.utc)
    else:
        # Convert to UTC if a different timezone is attached
        last_change = last_change.astimezone(timezone.utc)

    # 3. Calculate difference safely
    diff = now - last_change

    seconds = int(diff.total_seconds())
    if seconds < 0:
        return "just now"
    if seconds < 60:
        return f"{seconds}s"

    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"

    hours = minutes // 60
    if hours < 24:
        return f"{hours}h {minutes % 60}m"

    return f"{diff.days}d {hours % 24}h"


class PresenceMCPServer(MCPServer):
    """
    MCP Server implementation for tracking person/device presence.
    Provides real-time status, ISO timestamps, and relative duration.
    """

    def __init__(self, name: str, port: int, presences: List[Presence]):
        super().__init__(name, port)
        self.presences = presences

        @self.mcp.tool(name="get_presence_overview",
                       description="Returns a detailed report of all tracked entities. Includes status (PRESENT/AWAY), "
                                   "ISO timestamps, and relative duration. The entity 'any' represents the "
                                   "aggregate home state (PRESENT if at least one person is home).")
        def get_presence_overview() -> str:
            """
            Fetches a complete overview of all tracked entities.
            Useful for determining who is home and for how long.
            """
            try:
                if not self.presences:
                    return "No presence entities are currently being tracked."

                lines = []
                # Sort by presence: PRESENT entities appear first in the list
                sorted_presences = sorted(self.presences, key=lambda x: x.is_presence, reverse=True)

                for p in sorted_presences:
                    status = "PRESENT" if p.is_presence else "AWAY"

                    # Get relative duration string (e.g., '2h 15m')
                    duration = _get_duration_str(p.last_time_presence)

                    # Format timestamp; ensure we use UTC consistently
                    if p.last_time_presence:
                        ts_aware = p.last_time_presence if p.last_time_presence.tzinfo else p.last_time_presence.replace(tzinfo=timezone.utc)
                        timestamp = ts_aware.strftime("%Y-%m-%d %H:%M")
                    else:
                        timestamp = "Never"

                    # Build the summary line
                    lines.append(f"- {p.name}: {status} (since {duration}, last seen: {timestamp} UTC)")

                return "Current Home Presence Report:\n" + "\n".join(lines)

            except Exception as e:
                # Log the full stack trace for debugging, return simple error to the AI
                logging.warning(f"Failed to generate presence overview: {e}", exc_info=True)
                return f"Error generating presence overview: {e}"