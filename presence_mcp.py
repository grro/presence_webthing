from typing import List
from mcplib.server import MCPServer
from presence import Presence

class PresenceMCPServer(MCPServer):

    def __init__(self, name: str, port: int, presences: List[Presence]):
        super().__init__(name, port)
        self.presences = presences

        @self.mcp.tool(name="list_tracked_entities",
                       description="Returns a list of all tracked persons or devices. The entity 'all' represents the group state.")
        def list_tracked_entities() -> str:
            """Provides the names of all available presence sensors."""
            return ", ".join([p.name for p in self.presences])

        @self.mcp.tool(name="get_presence_info",
                       description="Returns the current presence status and the last seen timestamp for a specific person.")
        def get_presence_info(name: str) -> str:
            """
            Args:
                name: The name of the person or device to check.
            """
            for presence in self.presences:
                if presence.name == name:
                    status = "Present (1)" if presence.is_presence else "Away (0)"
                    last_seen = (presence.last_time_presence.strftime("%Y-%m-%dT%H:%M")
                                 if presence.last_time_presence else "Never")

                    return f"Entity: {name} | Status: {status} | Last Seen: {last_seen} UTC"

            available = ", ".join([p.name for p in self.presences])
            return f"Error: '{name}' not found. Available: {available}"