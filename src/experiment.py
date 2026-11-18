"""Shared reproducible experiment/export protocol for UI and command line."""
import csv
import hashlib
import io
import json
import platform
import time
import zipfile
from datetime import datetime, timezone
from importlib.metadata import version, PackageNotFoundError
import numpy as np
from nlm_lab import filter_image, metrics, png, quantize, intensity_range

METHODS = ['NLM tự cài đặt', 'NLM scikit-image', 'Mean', 'Gaussian', 'Median',
           'Bilateral', 'Median + NLM', 'Anscombe + NLM']
DEFAULTS = dict(sigma=20., h=8., patch=5, radius=5, kernel=3,
                gaussian=1., color=20., spatial=3., peak=30., anscombe_h=.8)


def installed_version(name):
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def benchmark(image, methods, params, repeats=3, warmup=True):
    if repeats < 1 or repeats > 20:
        raise ValueError('Số lần lặp phải từ 1 đến 20.')
    results = {}
    for method in methods:
        if method not in METHODS:
            raise ValueError(method)
        if warmup:
            filter_image(image, method, params)
        times = []
        for _ in range(repeats):
            start = time.perf_counter()
            out = filter_image(image, method, params)
            times.append(time.perf_counter() - start)
        results[method] = dict(image=quantize(out,image.dtype), seconds=float(np.median(times)),
                               times=times)
    return results


def csv_bytes(rows):
    out = io.StringIO(newline='')
    keys = list(dict.fromkeys(k for row in rows for k in row))
    writer = csv.DictWriter(out, fieldnames=keys)
    writer.writeheader()
    writer.writerows(rows)
    return ('\ufeff' + out.getvalue()).encode('utf-8')


def package(source, work, results, params, noise_config, has_gt,
            source_name='', fiji=None, fiji_config=None, repeats=1, warmup=False):
    rows = []
    if has_gt:
        rows.append(dict(method='Noisy input', **metrics(source, work), seconds=0.))
    files = {}
    for i, (name, record) in enumerate(results.items(), 1):
        files[name] = f'{i:02d}_result.png'
        rows.append(dict(method=name, **(metrics(source, record['image']) if has_gt else {}),
                         seconds=record['seconds']))
    if fiji is not None:
        if fiji.shape != work.shape or fiji.dtype!=work.dtype:
            raise ValueError('Ảnh Fiji phải cùng kích thước, số kênh và độ sâu bit.')
        rows.append(dict(method='Fiji', **(metrics(source, fiji) if has_gt else {})))
    comparisons = []
    if fiji is not None:
        for name, record in results.items():
            delta = record['image'].astype(float) - fiji.astype(float)
            comparisons.append(dict(method=name, MAE=float(np.abs(delta).mean()),
                                    max_abs=float(np.abs(delta).max())))
    source_file='source_rgb.png' if source.ndim==3 else 'source_gray.png'
    meta = dict(schema_version=3, created_utc=datetime.now(timezone.utc).isoformat(),
                source_name=source_name, parameters=params, noise=noise_config,
                ground_truth=has_gt, shape=list(work.shape), dtype=str(work.dtype),
                color_mode='RGB' if work.ndim==3 else 'grayscale', source_file=source_file, files=files,
                parameter_units='sigma, h, bilateral color: equivalent 0..255; spatial: pixels',
                input_png_sha256=hashlib.sha256(png(work)).hexdigest(),
                source_png_sha256=hashlib.sha256(png(source)).hexdigest(),
                fiji=fiji_config if fiji is not None else None,
                fiji_png_sha256=hashlib.sha256(png(fiji)).hexdigest() if fiji is not None else None,
                timing=dict(repeats=repeats, warmup=warmup, excludes='I/O, metrics, quantization',
                            statistic='median', runs={k:v['times'] for k,v in results.items()}),
                metric_protocol=dict(range=intensity_range(source), output='rounded clipped '+str(work.dtype),
                                     MSE='mean over pixels and channels, native intensity units squared',
                                     SSIM='7x7 uniform, sample covariance, valid interior mean; RGB: channel mean'),
                python=platform.python_version(), platform=platform.platform(),
                versions={n:installed_version(n) for n in ['numpy','scipy','scikit-image','PyWavelets','Pillow','streamlit','pypng','tifffile']})
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr(source_file, png(source))
        z.writestr('noisy_input.png', png(work))
        for name, record in results.items():
            z.writestr(files[name], png(record['image']))
        if fiji is not None:
            z.writestr('fiji_result.png', png(fiji))
            z.writestr('fiji_comparison.csv', csv_bytes(comparisons))
        z.writestr('metadata.json', json.dumps(meta, ensure_ascii=False, indent=2, allow_nan=False))
        z.writestr('metrics.csv', csv_bytes(rows))
    return buf.getvalue(), rows, comparisons
