"""Propose staff and bar regions; all coordinates refer to the saved page PNG.

This deliberately conservative first pass uses image morphology, not OMR. It
does not infer pitches, time signatures, or the number of bars in a multirest.
"""

import cv2
import numpy as np


def runs(values):
    indices = np.flatnonzero(values)
    if not len(indices):
        return []
    return np.split(indices, np.where(np.diff(indices) > 1)[0] + 1)


def detect_regions(image):
    gray = cv2.cvtColor(np.asarray(image.convert("RGB")), cv2.COLOR_RGB2GRAY)
    height, width = gray.shape
    binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    horizontal = cv2.morphologyEx(
        binary, cv2.MORPH_OPEN, np.ones((1, max(20, width // 28)), np.uint8))
    line_rows = [int(np.mean(group)) for group in runs((horizontal > 0).sum(axis=1) > width * .18)]
    staves = []
    index = 0
    while index + 4 < len(line_rows):
        lines = line_rows[index:index + 5]
        gaps = np.diff(lines)
        spacing = float(np.median(gaps))
        if 3 < spacing < max(25, height / 45) and np.max(np.abs(gaps - spacing)) < spacing * .65:
            staves.append((lines, spacing))
            index += 5
        else:
            index += 1

    regions = []
    for staff_index, (lines, spacing) in enumerate(staves):
        y1, y2 = lines[0], lines[-1]
        coverage = (horizontal[max(0, y1 - 2):y2 + 3] > 0).sum(axis=0)
        active = np.flatnonzero(coverage >= 3)
        if not len(active):
            continue
        left, right = int(active[0]), int(active[-1])
        staff = binary[y1:y2 + 1]
        vertical = cv2.morphologyEx(
            staff, cv2.MORPH_OPEN, np.ones((max(5, int((y2-y1)*.8)), 1), np.uint8))
        columns = runs((vertical > 0).sum(axis=0) >= (y2-y1)*.93)
        candidates = [int(np.mean(group)) for group in columns
                      if left + spacing * 7 < np.mean(group) < right - spacing]
        boundaries = [left]
        for x in candidates:
            if x - boundaries[-1] > spacing * 1.4:
                boundaries.append(x)
        if right - boundaries[-1] < spacing * 2:
            boundaries[-1] = right
        else:
            boundaries.append(right)
        # Include slurs, chord symbols, ledger lines and directions above/below the staff.
        previous = staves[staff_index-1][0][-1] if staff_index else 0
        following = staves[staff_index+1][0][0] if staff_index+1 < len(staves) else height
        top = max(0, int(max((previous+y1)/2 if staff_index else 0, y1-spacing*7)))
        bottom = min(height, int(min((y2+following)/2, y2+spacing*5)))
        for bar_index, (x1, x2) in enumerate(zip(boundaries, boundaries[1:])):
            if x2 - x1 < spacing * 2.5:
                continue
            regions.append({"staff_index": staff_index, "bar_index": bar_index,
                            "box": [max(0, x1-4), top, min(width, x2+5), bottom],
                            "staff_box": [max(0, left-15), top, min(width, right+15), bottom],
                            "staff_lines": lines, "detection": "unverified"})
    return regions
