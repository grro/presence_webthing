from typing import List
from mcp_server import MCPServer
from presence import Presence


class PresenceCPServer(MCPServer):

    def __init__(self, name: str, port: int, presences: List[Presence]):
        super().__init__(name, port)
        self.presences = presences


        @self.mcp.resource("presence://list/names")
        def list_awning_names() -> str:
            """Returns a comma-separated list of all available presences. The presence with the extension all is the group of all presences. """
            return ", ".join([awning.name for awning in self.presences])


        @self.mcp.resource("presences://{name}/is_presence")
        def is_presence(name: str) -> int:
            """
            Returns the current position of a specific awning.
            0 = fully open, 100 = fully closed.
            """
            for presence  in self.presences:
                if presence.name == name:
                    return presence.is_presence
            raise ValueError(f"presence '{name}' not found")

# npx @modelcontextprotocol/inspector

