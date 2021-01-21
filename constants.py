HEADER_LENGTH = 10


class Types:
    """
    Types describe the types of messages sent between the client and server.
    A message could be a request, a posting of information, a message etc.
    The Types class provides a universal naming for the types of messages that will be exchanged.
    """
    SERVER_MESSAGE = 'SERVER_MESSAGE'
    REQUEST = 'REQUEST'
    NICKNAME = 'NICKNAME'
    USER_LIST = 'USER_LIST'
    MESSAGE = 'MESSAGE'


class Requests:
    """
    Requests describe a request between the server and client to send a specific type of information.
    The Requests class provides a universal naming for the types of requests that can be made and received.
    """
    REQUEST_NICK = 'REQUEST_NICK'  # Send the server the client's nickname
    REFRESH_CONNECTIONS_LIST = 'REFRESH_CLIENT_LIST'  # Send the client all connections to the server and their information
    GET_HISTORY = 'GET_HISTORY'  # Send a short history of the chat to the client


class Colors:
    """
    Stores hexadecimal color codes of popular colors, with names.
    """

    ALL_NAMES = ['Aqua', 'Azure', 'Beige', 'Black', 'Blue', 'Brown', 'Cyan', 'Dark Blue', 'Dark Cyan', 'Dark Grey',
                 'Dark Green', 'Dark Khaki', 'Dark Magenta', 'Dark Olive Green', 'Dark Orange', ' Dark Orchid', 'Dark Red', 'Dark Salmon',
                 'Dark Violet', 'Fuchsia', 'Gold', 'Green', 'Indigo', 'Khaki', 'Light Blue', 'Light Cyan',
                 'Light Green', 'Light Grey', 'Light Pink', 'Light Yellow', 'Lime', 'Magenta', 'Maroon', 'Navy',
                 'Olive', 'Orange', 'Pink', 'Purple', 'Violet', 'Red', 'Silver', 'White', 'Yellow']
    ALL = [AQUA, AZURE, BEIGE, BLACK, BLUE, BROWN, CYAN, DARKBLUE, DARKCYAN, DARKGREY, DARKGREEN, DARKKHAKI,
           DARKMAGENTA, DARKOLIVEGREEN, DARKORANGE, DARKORCHID, DARKRED, DARKSALMON, DARKVIOLET, FUCHSIA, GOLD, GREEN,
           INDIGO, KHAKI, LIGHTBLUE, LIGHTCYAN, LIGHTGREEN, LIGHTGREY, LIGHTPINK, LIGHTYELLOW, LIME, MAGENTA, MAROON,
           NAVY, OLIVE, ORANGE, PINK, PURPLE, VIOLET, RED, SILVER, WHITE, YELLOW, ]
