class APIError(Exception):
    '''
    the base APIError which contains error(required, data(optional) and message(optional).
    '''

    def __init__(self, error, data='', message=''):
        super().__init__(message)
        self.error = error
        self.data = data
        self.message = message


class APIValueError(APIError):
    '''
    Indicate the input value has error or invalid.The data specifies the error field of input form.
    '''

    def __init__(self, field, message=''):
        super().__init__('value:invalid', field, message)
