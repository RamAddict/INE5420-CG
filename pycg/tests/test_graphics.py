from math import pi
from typing import Sequence
from blas import Matrix
from graphics import Bezier, Transformation, Point, Line, Polygon


def test_transformations_center_pivot():
    p = Point(5, 4)
    t = Transformation().translate(2, 1).matrix(pivot=p.center())
    p.transform(t)
    assert p == (7, 5)

    v = Line(Point(0, 0), Point(10, 0))
    r = Transformation().rotate(pi / 2).matrix(pivot=v.center())
    v.transform(r)
    a, b = v
    assert round(a.x) == 5
    assert round(a.y) == -5
    assert round(b.x) == 5
    assert round(b.y) == 5

    rect = Polygon([Point(-1, 1), Point(1, 1), Point(1, -1), Point(-1, -1)])
    s = Transformation().scale(4, 3).matrix(pivot=rect.center())
    rect.transform(s)
    upper_left, upper_right, lower_right, lower_left, close = rect
    assert close == upper_left
    assert upper_left == (-4, 3)
    assert upper_right == (4, 3)
    assert lower_right == (4, -3)
    assert lower_left == (-4, -3)


def test_transformations_global_pivot():
    p = Point(4, 2)
    s = Transformation().scale(-3).matrix(pivot=Point(0, 0))
    p.transform(s)
    assert p == (-12, -6)

    vertical_line = Line(Point(0, 0), Point(0, 300))
    translation_by_100 = Transformation().translate(100, 0).matrix(pivot=Point(0,0))
    vertical_line.transform(translation_by_100)
    point_a, point_b = vertical_line
    assert point_a.x == 100
    assert point_a.y == 0
    assert point_b.x == 100
    assert point_b.y == 300

    rotate_by_90 = Transformation().rotate(pi/2).matrix(pivot=Point(0,0))
    vertical_line.transform(rotate_by_90)
    point_a, point_b = vertical_line
    assert round(point_a.x) == 0
    assert round(point_a.y) == 100
    assert round(point_b.x) == -300
    assert round(point_b.y) == 100

def testBezier():
    curve = Bezier([Point(1,1), Point(2,2), Point(3,2), Point(4,1)], step=0.1)
    correctCurve = [Point(1.0, 1.0), Point(1.2999999523162842, 1.2699999809265137), Point(1.600000023841858, 1.4800000190734863), Point(1.9000000953674316, 1.6299999952316284), Point(2.1999998092651367, 1.71999990940094), Point(2.5, 1.75), Point(2.799999713897705, 1.7199996709823608), Point(3.0999999046325684, 1.6299998760223389), Point(3.4000000953674316, 1.4800002574920654), Point(3.6999998092651367, 1.269999623298645), Point(4.0, 1.0)]
    assert curve._points == correctCurve
