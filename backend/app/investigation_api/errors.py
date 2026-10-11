class ApiFailure(Exception):
    def __init__(self, code, message, *, status=500, retryable=False):
        super().__init__(code)
        self.code, self.message, self.status, self.retryable = code, message, status, retryable


def not_ready():
    return ApiFailure('RESULT_NOT_READY', '调查尚未产生该结果，请稍后查询。', status=409, retryable=True)
