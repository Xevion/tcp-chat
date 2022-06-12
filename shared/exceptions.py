class TCPChatException(BaseException):
    pass


class DataReceptionException(TCPChatException):
    pass


class StopException(TCPChatException):
    """An exception that occurs when a thread finds a stop flag."""
    pass
