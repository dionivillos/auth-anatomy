class ApiError(Exception):
    """A JSON API error mapped to the uniform ``{error: {code, message}}`` shape.

    Carries an HTTP status alongside a stable machine-readable ``code`` and a
    human ``message``, so a single exception handler can render every API error
    the same way.
    """

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
