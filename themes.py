"""Visual-condition helpers: contrast palettes, size presets and brightness maths.

This module contains no GUI code, so it can be tested on its own.

How the three visual variables are simulated
--------------------------------------------
* Contrast   - three grey text/object colours on a white background. Only
               luminance differs (no hue), so the manipulation is not confounded
               by colour vision.
* Size       - three font sizes and three figure sizes (a rough stand-in for
               visual angle; no real angle is computed).
* Brightness - both the text/object colour and the background colour are
               multiplied by the slider percentage, like turning down a screen.
"""

# Text/object colour (fg) and background colour (bg) for each contrast level.
CONTRAST_LEVELS = {
    "High": {"fg": "#000000", "bg": "#FFFFFF"},
    "Medium": {"fg": "#767676", "bg": "#FFFFFF"},
    "Low": {"fg": "#C2C2C2", "bg": "#FFFFFF"},
}

# Font size (points) and ambiguous-figure size (pixels) for each size level.
SIZE_LEVELS = {
    "Small": {"font": 10, "figure": 140},
    "Medium": {"font": 16, "figure": 220},
    "Large": {"font": 26, "figure": 320},
}

BRIGHTNESS_MIN = 30    # percent
BRIGHTNESS_MAX = 100   # percent
BRIGHTNESS_DEFAULT = 100


def hex_to_rgb(hex_colour):
    """'#RRGGBB' -> (r, g, b) with each channel 0-255."""
    h = hex_colour.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rgb_to_hex(rgb):
    """(r, g, b) -> '#RRGGBB'."""
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def scale_brightness(hex_colour, percent):
    """Return the colour dimmed to `percent` (100 = unchanged)."""
    factor = max(0.0, min(100.0, percent)) / 100.0
    r, g, b = hex_to_rgb(hex_colour)
    return rgb_to_hex((round(r * factor), round(g * factor), round(b * factor)))


def relative_luminance(hex_colour):
    """WCAG relative luminance (0 = black, 1 = white)."""
    def linear(channel):
        c = channel / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (linear(c) for c in hex_to_rgb(hex_colour))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(colour_a, colour_b):
    """WCAG contrast ratio between two colours (1.0 = identical, 21.0 = black/white)."""
    la, lb = relative_luminance(colour_a), relative_luminance(colour_b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def get_colours(contrast_name, brightness_percent=BRIGHTNESS_DEFAULT):
    """Return (fg, bg) hex colours for a contrast level at a brightness level."""
    palette = CONTRAST_LEVELS[contrast_name]
    return (scale_brightness(palette["fg"], brightness_percent),
            scale_brightness(palette["bg"], brightness_percent))
