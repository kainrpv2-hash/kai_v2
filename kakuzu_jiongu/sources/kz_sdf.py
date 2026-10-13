"""Signed-distance modelling helpers (numpy) + marching cubes, used to sculpt the creature bodies.

Coordinates: metres, Blender convention (Z up, creature faces -Y).
"""
import numpy as np
from skimage import measure


# ------------------------------------------------------------------ primitives
def sd_round_cone(P, a, b, r1, r2):
    """Tapered capsule from a (radius r1) to b (radius r2). IQ's exact sdRoundCone."""
    a = np.asarray(a, np.float64)
    b = np.asarray(b, np.float64)
    ba = b - a
    l2 = float(ba @ ba)
    rr = r1 - r2
    a2 = l2 - rr * rr
    il2 = 1.0 / l2
    pa = P - a
    y = pa @ ba
    z = y - l2
    xv = pa * l2 - np.outer(y, ba)
    x2 = np.einsum("ij,ij->i", xv, xv)
    y2 = y * y * l2
    z2 = z * z * l2
    k = np.sign(rr) * rr * rr * x2
    d_b = np.sqrt(x2 + z2) * il2 - r2
    d_a = np.sqrt(x2 + y2) * il2 - r1
    d_m = (np.sqrt(np.maximum(x2 * a2 * il2, 0.0)) + y * rr) * il2 - r1
    return np.where(np.sign(z) * a2 * z2 > k, d_b, np.where(np.sign(y) * a2 * y2 < k, d_a, d_m))


def rot_matrix(rx=0.0, ry=0.0, rz=0.0):
    """XYZ euler (degrees) -> 3x3 rotation matrix (applied as R @ v)."""
    rx, ry, rz = np.radians([rx, ry, rz])
    cx, sx, cy, sy, cz, sz = np.cos(rx), np.sin(rx), np.cos(ry), np.sin(ry), np.cos(rz), np.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def sd_ellipsoid(P, c, r, rot=(0, 0, 0)):
    R = rot_matrix(*rot)
    q = (P - np.asarray(c)) @ R  # world -> local
    r = np.asarray(r, np.float64)
    k0 = np.linalg.norm(q / r, axis=-1)
    k1 = np.linalg.norm(q / (r * r), axis=-1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


def smin(a, b, k):
    if k <= 0:
        return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1 - h) + a * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


# ------------------------------------------------------------------ noise
class Noise3:
    """Tileable value noise with quintic interpolation; fbm() and vector() helpers."""

    def __init__(self, seed=0, n=64):
        rng = np.random.default_rng(seed)
        self.g = rng.random((n, n, n)).astype(np.float64) * 2 - 1
        self.n = n

    def __call__(self, P):
        n = self.n
        Pf = np.floor(P)
        f = P - Pf
        i = Pf.astype(np.int64)
        u = f * f * f * (f * (f * 6 - 15) + 10)
        x0, y0, z0 = (i[:, 0] % n), (i[:, 1] % n), (i[:, 2] % n)
        x1, y1, z1 = (x0 + 1) % n, (y0 + 1) % n, (z0 + 1) % n
        g = self.g
        ux, uy, uz = u[:, 0], u[:, 1], u[:, 2]
        c00 = g[x0, y0, z0] * (1 - ux) + g[x1, y0, z0] * ux
        c10 = g[x0, y1, z0] * (1 - ux) + g[x1, y1, z0] * ux
        c01 = g[x0, y0, z1] * (1 - ux) + g[x1, y0, z1] * ux
        c11 = g[x0, y1, z1] * (1 - ux) + g[x1, y1, z1] * ux
        c0 = c00 * (1 - uy) + c10 * uy
        c1 = c01 * (1 - uy) + c11 * uy
        return c0 * (1 - uz) + c1 * uz

    def fbm(self, P, octaves=4, lac=2.03, gain=0.5):
        amp, s, tot = 1.0, 0.0, 0.0
        Q = P.copy()
        for o in range(octaves):
            s = s + amp * self(Q + o * 17.31)
            tot += amp
            amp *= gain
            Q = Q * lac
        return s / tot

    def vector(self, P, octaves=3):
        return np.stack([self.fbm(P, octaves), self.fbm(P + 31.7, octaves), self.fbm(P - 47.3, octaves)], axis=-1)


# ------------------------------------------------------------------ creature body SDF
class Body:
    """A creature body: smooth union of round cones / ellipsoids, then noise warping."""

    def __init__(self, seed=0):
        self.prims = []
        self.noise = Noise3(seed)
        self.warp_amp = 0.04
        self.warp_freq = 2.2
        self.lump_amp = 0.025
        self.lump_freq = 6.0
        self.carves = []
        self.bones = []

    def cone(self, a, b, r1, r2, k=0.12, bone=None):
        self.prims.append(("cone", (np.asarray(a, float), np.asarray(b, float), r1, r2), k))
        self.bones.append(bone)

    def chain(self, pts, radii, k=0.1, bones=None):
        """Limb as a chain of round cones through pts with radius per point (first joint blends with k)."""
        for i in range(len(pts) - 1):
            self.cone(pts[i], pts[i + 1], radii[i], radii[i + 1], k if i == 0 else 0.03,
                      bone=(bones[i] if bones else None))

    def ell(self, c, r, rot=(0, 0, 0), k=0.15, bone=None):
        self.prims.append(("ell", (np.asarray(c, float), np.asarray(r, float), rot), k))
        self.bones.append(bone)

    def carve_ell(self, c, r, rot=(0, 0, 0), k=0.05):
        self.carves.append(("ell", (np.asarray(c, float), np.asarray(r, float), rot), k))

    def bounds(self, margin=0.25):
        lo = np.array([1e9] * 3)
        hi = -lo
        for t, p, _ in self.prims:
            if t == "cone":
                a, b, r1, r2 = p
                rmax = max(r1, r2)
                lo = np.minimum(lo, np.minimum(a, b) - rmax)
                hi = np.maximum(hi, np.maximum(a, b) + rmax)
            else:
                c, r, _ = p
                rm = r.max()
                lo = np.minimum(lo, c - rm)
                hi = np.maximum(hi, c + rm)
        return lo - margin, hi + margin

    def _prim(self, P, t, p):
        if t == "cone":
            return sd_round_cone(P, *p)
        return sd_ellipsoid(P, *p)

    def sdf(self, P):
        Q = P + self.noise.vector(P * self.warp_freq) * self.warp_amp
        d = None
        for t, p, k in self.prims:
            di = self._prim(Q, t, p)
            d = di if d is None else smin(d, di, k)
        for t, p, k in self.carves:
            d = smax(d, -self._prim(Q, t, p), k)
        d = d + self.noise.fbm(P * self.lump_freq + 5.0, 3) * self.lump_amp
        return d

    def warp(self, P):
        return P + self.noise.vector(P * self.warp_freq) * self.warp_amp

    def bone_weights(self, P, bone_names, tau=0.06, max_inf=4, chunk=200_000):
        """Skin weights from primitive membership: each primitive belongs to a bone; a point is
        weighted by softmin of its distance to every bone's primitives (so an arm hanging next
        to the torso does not drag torso vertices along)."""
        out = np.zeros((len(P), len(bone_names)))
        for s in range(0, len(P), chunk):
            Q = self.warp(P[s:s + chunk])
            D = np.full((len(Q), len(bone_names)), 1e9)
            for (t, p, _), b in zip(self.prims, self.bones):
                if b is None:
                    continue
                j = bone_names.index(b)
                D[:, j] = np.minimum(D[:, j], self._prim(Q, t, p))
            D = np.maximum(D, 0.0)
            W = np.exp(-(D - D.min(1, keepdims=True)) / tau)
            out[s:s + chunk] = W
        order = np.argsort(-out, 1)
        out[np.arange(len(P))[:, None], order[:, max_inf:]] = 0
        out[out < 0.02] = 0
        return out / out.sum(1, keepdims=True)

    def surface_hit(self, x, z, y_from=-4.0, y_to=4.0, steps=4000):
        """Front-most surface point along +Y at (x, z) and the outward normal (SDF gradient)."""
        ys = np.linspace(y_from, y_to, steps)
        P = np.stack([np.full_like(ys, x), ys, np.full_like(ys, z)], 1)
        d = self.sdf(P)
        i = int(np.argmax(d < 0))
        y = ys[i]
        p = np.array([x, y, z])
        e = 0.01
        g = np.array([
            self.sdf(np.array([p + [e, 0, 0]]))[0] - self.sdf(np.array([p - [e, 0, 0]]))[0],
            self.sdf(np.array([p + [0, e, 0]]))[0] - self.sdf(np.array([p - [0, e, 0]]))[0],
            self.sdf(np.array([p + [0, 0, e]]))[0] - self.sdf(np.array([p - [0, 0, e]]))[0]])
        return p, g / np.linalg.norm(g)

    def mesh(self, voxel=0.02, chunk=400_000):
        lo, hi = self.bounds()
        shape = np.ceil((hi - lo) / voxel).astype(int) + 1
        xs = lo[0] + np.arange(shape[0]) * voxel
        ys = lo[1] + np.arange(shape[1]) * voxel
        zs = lo[2] + np.arange(shape[2]) * voxel
        G = np.stack(np.meshgrid(xs, ys, zs, indexing="ij"), axis=-1).reshape(-1, 3)
        vals = np.empty(len(G))
        for s in range(0, len(G), chunk):
            vals[s:s + chunk] = self.sdf(G[s:s + chunk])
        vol = vals.reshape(tuple(shape))
        # ground clip: nothing below z=0
        verts, faces, normals, _ = measure.marching_cubes(vol, level=0.0, spacing=(voxel, voxel, voxel))
        verts += lo
        return verts, faces
