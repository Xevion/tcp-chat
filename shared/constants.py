from typing import List
from collections import namedtuple

import os
import webcolors

__BASE_DIR = os.path.dirname(os.path.abspath(__file__))

HEADER_LENGTH = 10
MINIMUM_CONTRAST = 4.65
CLIENT_DATABASE = os.path.join(__BASE_DIR, 'client.db')
SERVER_DATABASE = os.path.join(__BASE_DIR, 'server.db')

DEFAULT_IP = "127.0.0.1"
DEFAULT_PORT = 5555

ConnectionOptions = namedtuple('ConnectionOptions', ['ip', 'port', 'nickname', 'password', 'remember'])


class Types:
    """
    Types describe the types of messages sent between the client and server.
    A message could be a request, a posting of information, a message etc.
    The Types class provides a universal naming for the types of messages that will be exchanged.
    """
    REQUEST = 'REQUEST'
    MESSAGE = 'MESSAGE'
    NICKNAME = 'NICKNAME'
    USER_LIST = 'USER_LIST'
    MESSAGE_HISTORY = 'MESSAGE_HISTORY'


class Requests:
    """
    Requests describe a request between the server and client to send a specific type of information.
    The Requests class provides a universal naming for the types of requests that can be made and received.
    """
    REQUEST_NICK = 'REQUEST_NICK'  # Send the server the client's nickname
    GET_MESSAGE_HISTORY = 'GET_MESSAGE_HISTORY'  # Send the client a detailed list of all messages sent up to a certain point.


class Color():
    """
    Describes a basic RGB color.
    """

    def __init__(self, name: str, hex: str) -> None:
        self.name, self.hex = name, hex
        self.rgb = webcolors.hex_to_rgb(hex)

    def __repr__(self) -> str:
        return f'Color({self.name})'

    @property
    def id(self) -> str:
        return '_'.join(self.name.split()).upper()

    def relative_luminance(self) -> float:
        """
        Calculates the relative luminance of a given color, according to WCAG guidelines.

        https://www.w3.org/TR/WCAG20/#relativeluminancedef

        :return: The relative luminance of this color.
        """
        r, g, b = self.rgb.red / 255, self.rgb.green / 255, self.rgb.blue / 255
        r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
        g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
        b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    def contrast_ratio(self, other: 'Color') -> float:
        """
        Calculates the relative contrast between two colors in a ratio from 1:1 to 21:1, according to WCAG guidelines.

        https://www.w3.org/TR/WCAG20/#contrast-ratiodef

        :param other: The darker color.
        :return:
        """
        l1 = self.relative_luminance()
        l2 = other.relative_luminance()
        return (l1 + 0.05) / (l2 + 0.05)


class Colors:
    """
    Stores hexadecimal color codes of popular colors, with names.
    """

    AQUA = Color("Aqua", "#00ffff")
    AZURE = Color("Azure", "#f0ffff")
    BEIGE = Color("Beige", "#f5f5dc")
    BLACK = Color("Black", "#000000")
    BLUE = Color("Blue", "#0000ff")
    BROWN = Color("Brown", "#a52a2a")
    CYAN = Color("Cyan", "#00ffff")
    DARKBLUE = Color("Dark Blue", "#00008b")
    DARKCYAN = Color("Dark Cyan", "#008b8b")
    DARKGREY = Color("Dark Grey", "#a9a9a9")
    DARKGREEN = Color("Dark Green", "#006400")
    DARKKHAKI = Color("Dark Khaki", "#bdb76b")
    DARKMAGENTA = Color("Dark Magenta", "#8b008b")
    DARKOLIVEGREEN = Color("Dark Olive Green", "#556b2f")
    DARKORANGE = Color("Dark Orange", "#ff8c00")
    DARKORCHID = Color("Dark Orchid", "#9932cc")
    DARKRED = Color("Dark Red", "#8b0000")
    DARKSALMON = Color("Dark Salmon", "#e9967a")
    DARKVIOLET = Color("Dark Violet", "#9400d3")
    FUCHSIA = Color("Fuchsia", "#ff00ff")
    GOLD = Color("Gold", "#ffd700")
    GREEN = Color("Green", "#008000")
    INDIGO = Color("Indigo", "#4b0082")
    KHAKI = Color("Khaki", "#f0e68c")
    LIGHTBLUE = Color("Light Blue", "#add8e6")
    LIGHTCYAN = Color("Light Cyan", "#e0ffff")
    LIGHTGREEN = Color("Light Green", "#90ee90")
    LIGHTGREY = Color("Light Grey", "#d3d3d3")
    LIGHTPINK = Color("Light Pink", "#ffb6c1")
    LIGHTYELLOW = Color("Light Yellow", "#ffffe0")
    LIME = Color("Lime", "#00ff00")
    MAGENTA = Color("Magenta", "#ff00ff")
    MAROON = Color("Maroon", "#800000")
    NAVY = Color("Navy", "#000080")
    OLIVE = Color("Olive", "#808000")
    ORANGE = Color("Orange", "#ffa500")
    PINK = Color("Pink", "#ffc0cb")
    PURPLE = Color("Purple", "#800080")
    VIOLET = Color("Violet", "#800080")
    RED = Color("Red", "#ff0000")
    SILVER = Color("Silver", "#c0c0c0")
    WHITE = Color("White", "#ffffff")
    YELLOW = Color("Yellow", "#ffff00")

    ALL = [AQUA, AZURE, BEIGE, BLACK, BLUE, BROWN, CYAN, DARKBLUE, DARKCYAN, DARKGREY, DARKGREEN, DARKKHAKI,
           DARKMAGENTA, DARKOLIVEGREEN, DARKORANGE, DARKORCHID, DARKRED, DARKSALMON, DARKVIOLET, FUCHSIA, GOLD, GREEN,
           INDIGO, KHAKI, LIGHTBLUE, LIGHTCYAN, LIGHTGREEN, LIGHTGREY, LIGHTPINK, LIGHTYELLOW, LIME, MAGENTA, MAROON,
           NAVY, OLIVE, ORANGE, PINK, PURPLE, VIOLET, RED, SILVER, WHITE, YELLOW]

    @staticmethod
    def has_contrast(ratio: float, background: Color = WHITE) -> List[Color]:
        """
        Returns a list of Color objects with contrast ratios above the given minimum.

        :param ratio: The minimum contrast ratio each color must adhere to.
        :param background: Defaults to White, the background (lighter) for the other contrasting colors to be compared to.
        :return: A list of Color objects with contrast ratios above the given minimum.
        """
        above_ratio = []

        for color in Colors.ALL:
            contrast = background.contrast_ratio(color)
            if contrast >= ratio:
                above_ratio.append(color)

        return above_ratio
