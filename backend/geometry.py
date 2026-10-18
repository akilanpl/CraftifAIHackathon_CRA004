"""Normalized polygon geometry; boundary points are inside."""
from math import isfinite


def cross(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def on_segment(p, a, b):
    return abs(cross(a, b, p)) < 1e-10 and min(a[0], b[0])-1e-10 <= p[0] <= max(a[0], b[0])+1e-10 and min(a[1], b[1])-1e-10 <= p[1] <= max(a[1], b[1])+1e-10


def intersects(a, b, c, d):
    return (cross(a,b,c)*cross(a,b,d) < 0 and cross(c,d,a)*cross(c,d,b) < 0) or any((on_segment(c,a,b),on_segment(d,a,b),on_segment(a,c,d),on_segment(b,c,d)))


def validate_polygon(points):
    if len(points) < 3 or len(points) > 64:
        raise ValueError('Polygon needs 3–64 vertices')
    if any(len(p) != 2 or any(not isfinite(v) or not 0 <= v <= 1 for v in p) for p in points):
        raise ValueError('Vertices must be finite normalized [x,y] coordinates')
    if len(set(tuple(p) for p in points)) != len(points):
        raise ValueError('Polygon vertices must be distinct; do not repeat closing vertex')
    n = len(points)
    for i, vertex in enumerate(points):
        previous, following = points[(i-1) % n], points[(i+1) % n]
        if on_segment(following, previous, vertex) or on_segment(previous, vertex, following):
            raise ValueError("Adjacent polygon edges cannot overlap or reverse direction")
    if abs(sum(points[i][0]*points[(i+1)%n][1]-points[(i+1)%n][0]*points[i][1] for i in range(n))) < 1e-8:
        raise ValueError('Polygon must have positive area')
    for i in range(n):
        for j in range(i+1,n):
            if j == i+1 or (i == 0 and j == n-1):
                continue
            if intersects(points[i],points[(i+1)%n],points[j],points[(j+1)%n]):
                raise ValueError('Polygon cannot self-intersect')
    return points


def point_in_polygon(point, polygon):
    inside = False
    x,y = point
    for i,a in enumerate(polygon):
        b = polygon[(i+1)%len(polygon)]
        if on_segment(point,a,b):
            return True
        if (a[1] > y) != (b[1] > y) and x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:
            inside = not inside
    return inside
