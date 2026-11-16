"""Run: python -m streamlit run nlm_lab.py. Grayscale/RGB, 8/16-bit lab."""
import io
import json
import time
import zipfile
import csv
import hashlib
import platform
from importlib.metadata import version
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
from scipy.ndimage import uniform_filter, gaussian_filter, median_filter
from skimage.restoration import denoise_nl_means, denoise_bilateral, estimate_sigma
from skimage.metrics import structural_similarity
from image_io import load_image, png, quantize, intensity_range, preview


def u8(x):
    return np.rint(np.clip(x, 0, 255)).astype(np.uint8)


def noise(x, kind, level, seed):
    if not np.isfinite(level) or level < 0:
        raise ValueError('Mức nhiễu phải hữu hạn và không âm.')
    if kind == 'Salt and pepper' and level > 1:
        raise ValueError('p phải trong [0,1].')
    if kind == 'Poisson' and level <= 0:
        raise ValueError('peak phải lớn hơn 0.')
    if kind not in ('Gaussian', 'Salt and pepper', 'Poisson'):
        raise ValueError('Mô hình nhiễu không hợp lệ.')
    rng = np.random.default_rng(seed)
    dtype=x.dtype
    maximum=intensity_range(x)
    x = x.astype(float)
    if kind == 'Gaussian':
        return quantize(x + rng.normal(0, level*maximum/255, x.shape),dtype)
    if kind == 'Salt and pepper':
        z = rng.random(x.shape[:2])
        out = x.copy()
        out[z < level / 2] = 0
        out[(z >= level / 2) & (z < level)] = maximum
        return quantize(out,dtype)
    if kind == 'Poisson':
        return quantize(rng.poisson(level * x / maximum) * maximum / level,dtype)
    return u8(x)


def nlm_own(x, patch=5, radius=10, h=8., sigma=20.):
    """Independent uniform-patch NLM, reflected boundaries, self weight 1.

    Vectorize over pixels; loop over offsets. Box-filtered squared distances
    cost O(H W (2r+1)^2), rather than another patch-area factor.
    This implements the stated NLM variant, not a port of the Fiji plugin.
    """
    if patch < 1 or patch % 2 != 1 or radius < 0 or h <= 0 or sigma < 0:
        raise ValueError('patch phải lẻ; radius >= 0; h > 0; sigma >= 0')
    x = np.asarray(x, dtype=np.float64)
    margin = radius + patch // 2
    padding=((margin,margin),(margin,margin))+(((0,0),) if x.ndim==3 else ())
    padded = np.pad(x, padding, mode='reflect') if margin else x
    height, width = x.shape[:2]
    base = padded[radius:radius + height + patch - 1,
                  radius:radius + width + patch - 1]
    numerator = np.zeros_like(x)
    denominator = np.zeros((height,width),dtype=float)
    k = patch // 2
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            shifted = padded[radius + dy:radius + dy + base.shape[0],
                             radius + dx:radius + dx + base.shape[1]]
            squared=(base-shifted)**2
            if x.ndim==3:squared=squared.mean(axis=-1)
            distance = uniform_filter(squared, size=patch,
                                      mode='reflect')[k:k + height, k:k + width]
            corrected = np.maximum(distance - 2 * sigma ** 2, 0)
            weight = np.exp(-corrected / h ** 2)
            center = shifted[k:k + height, k:k + width]
            numerator += (weight[...,None] if x.ndim==3 else weight) * center
            denominator += weight
    return numerator / (denominator[...,None] if x.ndim==3 else denominator)


def filter_image(x, method, p):
    maximum=intensity_range(x)
    scale=maximum/255
    return _filter_normalized(x.astype(float)/scale,method,p)*scale


def _filter_normalized(a, method, p):
    channel_axis=-1 if a.ndim==3 else None
    size=(p['kernel'],p['kernel'],1) if a.ndim==3 else p['kernel']
    if method == 'NLM tự cài đặt':
        return nlm_own(a, p['patch'], p['radius'], p['h'], p['sigma'])
    if method == 'NLM scikit-image':
        return denoise_nl_means(a, patch_size=p['patch'], patch_distance=p['radius'],
                               h=p['h'], sigma=p['sigma'], fast_mode=True,
                               preserve_range=True, channel_axis=channel_axis)
    if method == 'Mean':
        return uniform_filter(a, size=size, mode='reflect')
    if method == 'Gaussian':
        return gaussian_filter(a, sigma=(p['gaussian'],p['gaussian'],0) if a.ndim==3 else p['gaussian'], mode='reflect')
    if method == 'Median':
        return median_filter(a, size=size, mode='reflect')
    if method == 'Bilateral':
        return denoise_bilateral(a / 255, sigma_color=p['color'] / 255,
                                sigma_spatial=p['spatial'], mode='reflect', channel_axis=channel_axis) * 255
    if method == 'Median + NLM':
        pre = median_filter(a, size=size, mode='reflect')
        return nlm_own(pre, p['patch'], p['radius'], p['h'], p['sigma'])
    if method == 'Anscombe + NLM':
        peak = p['peak']
        counts = a * peak / 255
        z = 2 * np.sqrt(counts + 3 / 8)
        filtered = nlm_own(z, p['patch'], p['radius'], p.get('anscombe_h', .8), 1.)
        return np.maximum((filtered / 2) ** 2 - 3 / 8, 0) * 255 / peak
    raise ValueError('Phương pháp không hợp lệ: ' + method)


def metrics(reference, result):
    if reference.shape != result.shape:
        raise ValueError('Ảnh phải cùng kích thước và căn chỉnh pixel.')
    if min(reference.shape[:2]) < 7:
        raise ValueError('SSIM cần ảnh tối thiểu 7 x 7.')
    mse = float(np.mean((reference.astype(float) - result.astype(float)) ** 2))
    maximum=intensity_range(reference)
    return {'MSE': mse, 'PSNR_dB': float('inf') if mse == 0 else 10 * np.log10(maximum ** 2 / mse),
            'SSIM': float(structural_similarity(reference, result, data_range=maximum, channel_axis=-1 if reference.ndim==3 else None,
                           win_size=7, gaussian_weights=False, use_sample_covariance=True))}


def main():
    from app_ui import main as app_main
    app_main()


if __name__ == '__main__':
    from app_ui import main as app_main
    app_main()
