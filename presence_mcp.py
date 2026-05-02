import asyncio
import logging
from typing import Protocol, cast, List, Dict
from fastmcp import FastMCP
from pydantic import AnyUrl, TypeAdapter
from datetime import datetime, timezone

from presence import Presence


logger = logging.getLogger(__name__)



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



class ResourceUpdateSession(Protocol):
    async def send_resource_updated(self, uri: AnyUrl) -> None:
        ...



class PresenceMCPServer:
    def __init__(self, name: str, port: int, presences: List[Presence], host: str = "0.0.0.0"):
        self.name = name
        self.host = host
        self.port = port

        self.mcp = FastMCP(self.name)
        self.active_sessions: set[ResourceUpdateSession] = set()
        self.low_level_server = self.mcp._mcp_server
        self.presences = presences
        self.loop = asyncio.new_event_loop()
        self.last_state: Dict[str, bool] = dict()
        [presence.add_listener(self.__on_value_changed) for presence in self.presences]


        @self.mcp.resource("sensor://presence")
        def get_presence_names() -> str:
            """
            Returns a comma-separated list of all available presence sensors.

            This resource helps the client discover which entities (e.g., specific
            entities or the 'any' aggregate) are currently tracked by the server.
            The returned names can then be used to query the detailed status
            via the 'sensor://presence/{name}' resource.
            """
            names = [p.name for p in self.presences]
            if not names:
                return "No sensors available."
            return "Available sensors: " + ", ".join(names)


        @self.mcp.resource("sensor://presence/{name}")
        def get_presence(name: str) -> str:
            """
            Retrieves the detailed presence status for a specific entity by its name.

            This resource provides the current state (PRESENT or AWAY)
            Crucially, accessing this resource automatically registers the client's
            session to receive real-time push notifications whenever this specific
            sensor's state changes in the future.

            Args:
                name: The exact name of the sensor/entity (e.g., 'Alice' or 'any').

            Returns:
                A formatted string containing the presence details, or an error
                message if the requested sensor name is not found.
            """

            # 1. Session registration
            try:
                req_ctx = self.low_level_server.request_context
                if req_ctx and req_ctx.session and req_ctx.session not in self.active_sessions:
                    self.active_sessions.add(cast(ResourceUpdateSession, req_ctx.session))
                    logger.info(f"[Server] Client session registered for updates (Resource: {name}).")
            except Exception as e:
                # FIX 2: Log the exception instead of silently ignoring it
                logger.debug(f"[Server] Could not register session: {e}")

            # 2. Search and format presence
            for p in self.presences:
                if p.name == name:
                    status = "PRESENT" if p.is_presence else "AWAY"
                    return f"- {p.name}: {status}"

            return f"Error: Sensor for '{name}' not found."


        @self.mcp.tool(name="presence_overview")
        def get_presence_overview() -> str:
            """
            Retrieves a comprehensive, real-time overview of all tracked presence entities.

            This tool aggregates the current state of all configured sensors (e.g., specific
            individuals or the collective 'any' state) into a single report. The results
            are intentionally sorted so that entities currently marked as 'PRESENT' appear
            at the top of the list, making it easy to quickly see who is home.

            Returns:
                str: A formatted, multi-line string report. Each line details an entity's
                     name, current status (PRESENT or AWAY), the relative time elapsed since
                     their last state change, and the exact UTC timestamp. If an internal
                     error occurs, a string describing the error is returned instead.
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



    def __on_value_changed(self, name: str):
        asyncio.run_coroutine_threadsafe(self._trigger_client_notification(name), self.loop)


    async def _trigger_client_notification(self, name: str) -> None:
        if not self.active_sessions:
            return

        for presence in self.presences:
            if presence.name == name:
                last_state = self.last_state.get(name, None)
                if presence.is_presence != last_state:
                    self.last_state[name] = presence.is_presence
                    dead_sessions = set()
                    for session in self.active_sessions:
                        try:
                            logger.info("[Server] Sende Update an Client...")
                            await session.send_resource_updated(TypeAdapter(AnyUrl).validate_python("sensor://presence/" + name))
                        except Exception as e:
                            logger.warning("[Server] Client nicht mehr erreichbar: %s", e)
                            dead_sessions.add(session)

                    self.active_sessions.difference_update(dead_sessions)
                break

    async def __run(self) -> None:
        logger.info(f"MCP Server '{self.name}' running on http://{self.host}:{self.port}/sse")
        await self.mcp.run_async(transport="sse", host=self.host, port=self.port)


    def start(self):
        # self._register_mdns()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.__run())
        finally:
            self.loop.close()


    def stop(self):
        # self._unregister_mdns()
        self.loop.stop()
        logging.info("MCP Server stopped")