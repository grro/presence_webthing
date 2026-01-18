import logging
from typing import List
from datetime import datetime, timezone
from mcplib.server import MCPServer
from presence import Presence


def _get_duration_str(last_change: datetime) -> str:
    """
    Calculates a human-readable duration string since the last state change.
    Example outputs: '45s', '12m', '3h 15m', '2d 4h'
    """
    if not last_change:
        return "unknown duration"

    # Compare using UTC to avoid timezone offset errors
    now = datetime.now(timezone.utc)
    diff = now - last_change

    seconds = int(diff.total_seconds())
    if seconds < 0: # Handle slight clock drifts
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
    MCP Server for monitoring the presence of people or devices.
    Tracks real-time status, timestamps, and absence/presence durations.
    """

    def __init__(self, name: str, port: int, presences: List[Presence]):
        super().__init__(name, port)
        self.presences = presences

        @self.mcp.tool(name="get_presence_overview",
                       description="Returns a detailed report of all tracked entities. Includes status (PRESENT/AWAY), ISO timestamps, and relative duration. The entity 'all' represents the aggregate home state (PRESENT if anyone is home).")
        def get_presence_overview() -> str:
            """
            Generates a comprehensive summary of all presence sensors.
            Use this to answer questions about who is currently home or how long they have been away.
            """
            try:
                if not self.presences:
                    return "No presence entities are currently being tracked."

                lines = []
                sorted_presences = sorted(self.presences, key=lambda x: x.is_presence, reverse=True)
                for p in sorted_presences:
                    # Determine status label
                    status = "PRESENT" if p.is_presence else "AWAY"

                    # Calculate relative duration (e.g., 2h 15m)
                    duration = _get_duration_str(p.last_time_presence)

                    # Format full ISO 8601 timestamp for unambiguous dating
                    timestamp = p.last_time_presence.strftime("%Y-%m-%d %H:%M") if p.last_time_presence else "Never"

                    # Construct line: e.g., - Lukas: PRESENT (since 2h 15m, last seen: 2026-01-18 14:30 UTC)
                    lines.append(f"- {p.name}: {status} (since {duration}, last seen: {timestamp} UTC)")

                return "Current Home Presence Report:\n" + "\n".join(lines)
            except Exception as e:
                logging.warning(e, exc_info=True)
                return f"Error generating presence overview: {e}"

