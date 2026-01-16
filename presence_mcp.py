from typing import List, Optional
from mcp_server import MCPServer
from presence import Presence

class PresenceMCPServer(MCPServer):

    def __init__(self, name: str, port: int, presences: List[Presence]):
        super().__init__(name, port)
        self.presences = presences

    def _find_presence(self, name: str) -> Optional[Presence]:
        for p in self.presences:
            if p.name == name:
                return p
        return None

    def _error_not_found(self, name: str) -> str:
        names = ", ".join([p.name for p in self.presences])
        return f"Error: Person '{name}' not found. Available names: {names}"


    def register_tools(self):

        @self.mcp.tool(name="list_tracked_persons",
                       description="Returns a comma-separated list of all tracked names. 'all' represents the group state.")
        def list_tracked_persons() -> str:
            return ", ".join([p.name for p in self.presences])

        @self.mcp.tool(name="get_presence_status",
                       description="Returns '1' if the person is present (at home), '0' if away.")
        def get_presence_status(name: str) -> str:
            p = self._find_presence(name)
            if p:
                return str(p.is_presence)
            return self._error_not_found(name)

        @self.mcp.tool(name="get_last_seen",
                       description="Retrieves the last seen UTC timestamp in ISO8601 format (YYYY-MM-DDTHH:MM).")
        def get_last_seen(name: str) -> str:
            p = self._find_presence(name)
            if p:
                if p.last_time_presence is None:
                    return "Never"
                return p.last_time_presence.strftime("%Y-%m-%dT%H:%M")
            return self._error_not_found(name)