"""Numerical checks against a slow independent NLM oracle on tiny arrays."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from nlm_lab import nlm_own, noise, metrics, filter_image, png, load_image
import io


def direct(x, patch, radius, h, sigma):
    f = patch // 2
    pad = radius + f
    a = np.pad(x.astype(float), pad, mode='reflect')
    out = np.empty_like(x, dtype=float)
    for y in range(x.shape[0]):
        for x0 in range(x.shape[1]):
            yy, xx = y + pad, x0 + pad
            p = a[yy-f:yy+f+1, xx-f:xx+f+1]
            total, weight = 0., 0.
            for dy in range(-radius, radius+1):
                for dx in range(-radius, radius+1):
                    q = a[yy+dy-f:yy+dy+f+1, xx+dx-f:xx+dx+f+1]
                    d = max(float(np.mean((p-q)**2)) - 2*sigma**2, 0)
                    w = np.exp(-d/h**2)
                    total += w*a[yy+dy, xx+dx]
                    weight += w
            out[y,x0] = total/weight
    return out


rng = np.random.default_rng(5)
x = rng.integers(0, 256, size=(9, 11), dtype=np.uint8)
for patch in [1, 3, 5]:
    for radius in [0, 1, 2]:
        expected = direct(x, patch, radius, 30., 10.)
        np.testing.assert_allclose(nlm_own(x, patch, radius, 30., 10.), expected, atol=1e-9)
np.testing.assert_allclose(nlm_own(np.full((9,11), 87), 5, 2, 8, 20), 87, atol=1e-12)
assert metrics(x, x) == {'MSE':0., 'PSNR_dB':float('inf'), 'SSIM':1.}
assert np.array_equal(load_image(io.BytesIO(png(x))), x)
for kind, level in [('Gaussian',20), ('Salt and pepper',.05), ('Poisson',30)]:
    assert np.array_equal(noise(x,kind,level,42), noise(x,kind,level,42))
    assert not np.array_equal(noise(x,kind,level,42), noise(x,kind,level,43))
p = dict(patch=3,radius=2,h=8.,sigma=20.,kernel=3,gaussian=1.,color=20.,spatial=3.)
for name in ['NLM tự cài đặt','NLM scikit-image','Mean','Gaussian','Median','Bilateral']:
    out = filter_image(x,name,p)
    assert out.shape == x.shape and np.isfinite(out).all()
    metrics(x,out)
try:
    metrics(x, x[:7])
except ValueError:
    pass
else:
    raise AssertionError('shape mismatch not rejected')
print('PASS: nine oracle comparisons, constant image, metrics, PNG roundtrip, seeded noise, six filters, shape validation')
