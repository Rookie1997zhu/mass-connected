class PipelineError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class PipelineSkip(PipelineError):
    """可跳过的候选（无字幕等），不记为硬失败时可选用。"""
