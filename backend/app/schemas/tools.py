from pydantic import BaseModel


class EngineStatus(BaseModel):
    available: bool
    name: str | None


class ToolsStatus(BaseModel):
    engines: dict[str, EngineStatus]
