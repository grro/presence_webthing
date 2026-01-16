from typing import List
from mcp_server import MCPServer
from presence import Presence

class PresenceMCPServer(MCPServer):

    def __init__(self, name: str, port: int, presences: List[Presence]):
        super().__init__(name, port)
        self.presences = presences

        @self.mcp.tool(name="list_tracked_persons", description="Returns a comma-separated list of all names of persons/devices currently being tracked. The entity named 'all' represents the group state (returns 1 if at least one person is present). Use these names as input for 'get_presence_status' or 'get_last_seen'.")
        def list_tracked_persons() -> str:
            """
            Provides the inventory of available presence sensors.
            """
            return ", ".join([p.name for p in self.presences])

        @self.mcp.tool(name="get_presence_status", description="Checks if a specific person/device is currently present. Returns '1' for present (at home) and '0' for away.")
        def get_presence_status(name: str) -> str:
            """
            Returns the status of a specific person.

            Args:
                name: The name of the person/device (from list_tracked_persons).

            Returns:
                "1" if present, "0" if away, or an error message containing valid names.
            """
            for presence in self.presences:
                if presence.name == name:
                    return str(presence.is_presence)

            return f"Error: Person '{name}' not found. Available names: {', '.join([p.name for p in self.presences])}"

        @self.mcp.tool(name="get_last_seen", description="Retrieves the last seen timestamp for a specific person/device in ISO8601 format (YYYY-MM-DDTHH:MM).")
        def get_last_seen(name: str) -> str:
            """
            Retrieves the last seen timestamp for a specific person/device.

            Args:
                name: The name of the person/device (from list_tracked_persons).
            Returns:
                The last seen timestamp as a string, 'Never' if no data exists, or an error message.
            """
            for presence in self.presences:
                if presence.name == name:
                    if presence.last_time_presence is None:
                        return "Never"

                    return presence.last_time_presence.strftime("%Y-%m-%dT%H:%M")

            return f"Error: Person '{name}' not found. Available names: {', '.join([p.name for p in self.presences])}"