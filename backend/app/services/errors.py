class ToolError(Exception):
    """Fallo esperado (archivo dañado, con contraseña…) con un mensaje apto para la persona usuaria."""

    def __init__(self, user_message: str) -> None:
        super().__init__(user_message)
        self.user_message = user_message


class EngineUnavailableError(ToolError):
    """Falta el programa externo que necesita la herramienta (p. ej. Office)."""
