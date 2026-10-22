"""Expected compiler failures, retaining completed stages for display."""


class CompilationError(Exception):
    def __init__(self, stage, message, line=None, column=None, partial_result=None):
        self.stage = stage
        self.message = message
        self.line = line
        self.column = column
        self.partial_result = partial_result or {}
        super().__init__(message)

    def __str__(self):
        position = ""
        if self.line is not None:
            position = f"Line {self.line}"
            if self.column is not None:
                position += f", column {self.column}"
            position += ": "
        return f"[{self.stage}] {position}{self.message}"
