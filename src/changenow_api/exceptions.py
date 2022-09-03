import json


class ChangeNowApiError(BaseException):
    def __init__(self, reason, code='', body=''):
        self.reason = reason
        self.code = code
        self.body = json.loads(body)
