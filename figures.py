"""Geometry for the two ambiguous figures used in the Identification task.

Only coordinates are produced here (no GUI calls), so the shapes can be tested
and previewed without Tkinter. app.py turns the coordinates into canvas items.

Figures
-------
* Necker cube - a wireframe cube whose "front" face seems to flip.
* Rubin's vase - a vase silhouette whose edges are also two face profiles.
"""

# Half-width of the vase at relative heights t (0 = top, 1 = bottom), as a
# fraction of the figure size. The bumps in the middle act as nose, lips and
# chin of the two facing profiles.
_VASE_PROFILE = [
    (0.00, 0.21), (0.07, 0.17), (0.15, 0.135), (0.23, 0.115),
    (0.29, 0.070), (0.34, 0.115), (0.40, 0.125), (0.44, 0.095),
    (0.48, 0.125), (0.52, 0.095), (0.58, 0.135), (0.64, 0.115),
    (0.71, 0.150), (0.80, 0.215), (0.90, 0.265), (1.00, 0.280),
]


def necker_cube_lines(cx, cy, size):
    """Return 12 line segments ((x1, y1), (x2, y2)) forming a Necker cube."""
    s = size * 0.55          # side of each square
    d = s * 0.38             # diagonal offset between the two squares
    # Square A (lower-left) and square B (upper-right).
    ax0, ay0 = cx - s / 2 - d / 2, cy - s / 2 + d / 2
    bx0, by0 = ax0 + d, ay0 - d
    a = [(ax0, ay0), (ax0 + s, ay0), (ax0 + s, ay0 + s), (ax0, ay0 + s)]
    b = [(bx0, by0), (bx0 + s, by0), (bx0 + s, by0 + s), (bx0, by0 + s)]
    lines = []
    for i in range(4):
        lines.append((a[i], a[(i + 1) % 4]))   # edges of square A
        lines.append((b[i], b[(i + 1) % 4]))   # edges of square B
        lines.append((a[i], b[i]))             # joining edges
    return lines


def vase_frame(cx, cy, size):
    """Return the (x0, y0, x1, y1) rectangle that forms the dark 'face' area."""
    return (cx - size * 0.5, cy - size * 0.55, cx + size * 0.5, cy + size * 0.55)


def _half_width(t):
    """Linear interpolation of the vase half-width at relative height t."""
    for (t0, w0), (t1, w1) in zip(_VASE_PROFILE, _VASE_PROFILE[1:]):
        if t0 <= t <= t1:
            return w0 + (w1 - w0) * (t - t0) / (t1 - t0)
    return _VASE_PROFILE[-1][1]


def vase_polygon(cx, cy, size):
    """Return the vase outline as a flat list [x1, y1, x2, y2, ...]."""
    height = size * 1.1
    top = cy - height / 2
    left, right = [], []
    steps = 60
    for i in range(steps + 1):
        t = i / steps
        y = top + t * height
        w = _half_width(t) * size
        left.append((cx - w, y))
        right.append((cx + w, y))
    points = left + right[::-1]            # down the left, back up the right
    return [coord for point in points for coord in point]
