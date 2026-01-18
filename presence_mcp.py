from typing import List
from datetime import datetime, timezone
from mcplib.server import MCPServer
from presence import Presence

class PresenceMCPServer(MCPServer):

    def __init__(self, name: str, port: int, presences: List[Presence]):
        super().__init__(name, port)
        self.presences = presences


        @self.mcp.tool(name="get_presence_overview",
                       description="Provides status, full ISO timestamp, and duration for all tracked entities.")
        def get_presence_overview() -> str:
            """Detailed report including full date and elapsed time."""
            if not self.presences:
                return "No entities tracked."

            lines = []
            for p in self.presences:
                status = "PRESENT" if p.is_presence else "AWAY"
                duration = self._get_duration_str(p.last_time_presence)

                # Full ISO 8601 timestamp: YYYY-MM-DD HH:MM
                timestamp = (p.last_time_presence.strftime("%Y-%m-%dT%H:%M")
                             if p.last_time_presence else "Never")

                # Format: - Name: STATUS (since 2h 15m, last seen: 2024-05-20 14:30 UTC)
                lines.append(f"- {p.name}: {status} (since {duration}, last seen: {timestamp} UTC)")

            return "Current Home Presence Report:\n" + "\n".join(lines)