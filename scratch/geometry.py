"""Two exact solvers for an ideal two-dimensional horizontal mirror."""
from fractions import Fraction as F


def clip(a, b, box):
    low, high = F(0), F(1)
    for p, q, mn, mx in zip(a, b, box[:2], box[2:]):
        if p == q:
            if not mn <= p <= mx:
                return False
            continue
        ends = sorted((F(mn-p, q-p), F(mx-p, q-p)))
        low, high = max(low, ends[0]), min(high, ends[1])
    return low <= high


def edges(a, b, box):
    x, y, u, v = box

    def inside(p):
        return x <= p[0] <= u and y <= p[1] <= v

    def side(p, q, r):
        return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])

    corners = [(x,y), (u,y), (u,v), (x,v)]
    return inside(a) or inside(b) or any(
        side(a,b,c)*side(a,b,d) <= 0 and side(c,d,a)*side(c,d,b) <= 0
        and all(max(min(a[i],b[i]),min(c[i],d[i])) <= min(max(a[i],b[i]),max(c[i],d[i])) for i in range(2))
        for c,d in zip(corners, corners[1:]+corners[:1])
    )


def solve(scene, independent=False):
    c, t = scene['camera'], scene['target']
    h, k = c[1], t[1]
    if independent:
        # Equal signed slopes measured against the normal.
        x = (F(c[0],h) + F(t[0],k)) / (F(1,h) + F(1,k))
        intersects = edges
    else:
        # Unfold the target across the reflecting plane.
        x = c[0] + F(h,h+k)*(t[0]-c[0])
        intersects = clip
    p = (x, 0)
    hit = scene['mirror'][0] <= x <= scene['mirror'][1]
    blockers = [name for name, box in scene['blocks'].items() if hit and
                (intersects(c,p,box) or intersects(p,t,box))]
    return hit and not blockers, blockers, x


def checked(scene):
    expected = solve(scene)
    if expected != solve(scene, independent=True):
        raise ValueError('Independent methods disagree')
    return expected
