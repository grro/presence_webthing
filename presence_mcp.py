from typing import List
from mcp_server import MCPServer
from presence import Presence


class PresenceMCPServer(MCPServer):

    def __init__(self, name: str, port: int, presences: List[Presence]):
        super().__init__(name, port)
        self.presences = presences

        @self.mcp.tool(name="list_presences", description="Returns a comma-separated list of all available presence sensors. The presence with the extension 'all' is the group of all presences.")
        def list_presences() -> str:
            return ", ".join([p.name for p in self.presences])

        @self.mcp.tool(name="get_presence_status", description="Returns the current status of a specific presence sensor. 1 = presence detected, 0 = no presence.")
        def get_presence_status(name: str) -> int:
            for presence in self.presences:
                if presence.name == name:
                    return presence.is_presence

            raise ValueError(f"presence '{name}' not found")



# npx @modelcontextprotocol/inspector

