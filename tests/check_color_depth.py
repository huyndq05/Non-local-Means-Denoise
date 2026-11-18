"""RGB/16-bit regressions: lossless I/O, channel isolation, joint NLM, exports."""
import io
import json
import sys
import zipfile
from pathlib import Path
SRC=Path(__file__).resolve().parents[1]/'src'
sys.path.insert(0,str(SRC))
import numpy as np
import tifffile
from PIL import Image
from image_io import load_image, png, preview, intensity_range
from nlm_lab import noise, filter_image, metrics, nlm_own
from experiment import benchmark, DEFAULTS, METHODS, package
from streamlit.testing.v1 import AppTest

rng=np.random.default_rng(9)
p=DEFAULTS.copy();p.update(patch=3,radius=1)
for shape in [(12,14),(12,14,3)]:
 for dtype in [np.uint8,np.uint16]:
  maximum=np.iinfo(dtype).max
  x=rng.integers(0,maximum+1,shape,dtype=dtype)
  np.testing.assert_array_equal(load_image(io.BytesIO(png(x)),color=True),x)
  tf=io.BytesIO();tifffile.imwrite(tf,x,photometric='rgb' if len(shape)==3 else 'minisblack')
  np.testing.assert_array_equal(load_image(io.BytesIO(tf.getvalue()),color=True),x)
  assert preview(x).dtype==np.uint8 and preview(x).shape==shape
  assert metrics(x,x)==dict(MSE=0.,PSNR_dB=float('inf'),SSIM=1.)
  for kind,level in [('Gaussian',20),('Salt and pepper',.1),('Poisson',30)]:
   v=noise(x,kind,level,42)
   assert v.dtype==dtype and v.shape==shape
   np.testing.assert_array_equal(v,noise(x,kind,level,42))
  results=benchmark(x,METHODS,p,1,False)
  for record in results.values():
   assert record['image'].shape==shape and record['image'].dtype==dtype
   score=metrics(x,record['image'])
   assert np.isfinite(score['MSE']) and np.isfinite(score['SSIM']) and not np.isnan(score['PSNR_dB'])
  payload,rows,_=package(x,x,results,p,None,True,fiji=x)
  with zipfile.ZipFile(io.BytesIO(payload)) as z:
   meta=json.loads(z.read('metadata.json'))
   assert meta['metric_protocol']['range']==maximum and meta['dtype']==str(x.dtype)
   for method,filename in meta['files'].items():
    np.testing.assert_array_equal(load_image(io.BytesIO(z.read(filename)),color=True),results[method]['image'])
   np.testing.assert_array_equal(load_image(io.BytesIO(z.read(meta['source_file'])),color=True),x)

# Spatial filters may never mix RGB channels, even with large spatial kernels.
x=np.zeros((12,14,3),dtype=np.uint16);x[:]=[12000,30000,60000]
for method in ['NLM tự cài đặt','NLM scikit-image','Mean','Gaussian','Median','Median + NLM']:
 np.testing.assert_allclose(filter_image(x,method,p),x,atol=1e-8)
# Joint RGB distance must reduce to the grayscale oracle for identical channels.
gray=rng.integers(0,256,(9,11),dtype=np.uint8)
rgb=np.repeat(gray[...,None],3,axis=-1)
np.testing.assert_allclose(nlm_own(rgb,3,1,8,20),np.repeat(nlm_own(gray,3,1,8,20)[...,None],3,axis=-1),atol=1e-9)
# Same relative error gives same PSNR/SSIM at either depth.
a=np.full((12,14,3),100,dtype=np.uint8);b=a+10
a16=a.astype(np.uint16)*257;b16=b.astype(np.uint16)*257
np.testing.assert_allclose(metrics(a,b)['PSNR_dB'],metrics(a16,b16)['PSNR_dB'],atol=1e-12)
np.testing.assert_allclose(metrics(a,b)['SSIM'],metrics(a16,b16)['SSIM'],atol=1e-12)
assert metrics(a16,b16)['MSE']==metrics(a,b)['MSE']*257**2
# Transparent input is explicitly flattened onto white.
rgba=np.zeros((8,8,4),dtype=np.uint8);rgba[:]=[255,0,0,0]
buf=io.BytesIO();Image.fromarray(rgba).save(buf,format='PNG')
assert (load_image(buf,color=True)==255).all()
# Reject float TIFF rather than silently clipping it.
buf=io.BytesIO();tifffile.imwrite(buf,np.ones((8,8),np.float32))
try:load_image(buf,color=True)
except ValueError:pass
else:raise AssertionError('float TIFF accepted without explicit intensity policy')

app=AppTest.from_file(str(SRC/'nlm_lab.py'),default_timeout=90).run()
assert not app.exception,app.exception
assert app.session_state['work'].ndim==3
next(s for s in app.selectbox if s.label=='Vùng ảnh thực hành').set_value('Crop giữa 128 × 128').run()
next(b for b in app.button if b.label=='Tạo nhiễu từ ảnh gốc').click().run()
next(c for c in app.checkbox if c.label=='Ước lượng sigma bằng wavelet').set_value(True).run()
next(s for s in app.multiselect if s.label=='Phương pháp cần chạy').set_value(['NLM tự cài đặt','NLM scikit-image']).run()
next(b for b in app.button if b.label=='Khử nhiễu và so sánh').click().run()
assert not app.exception,app.exception
assert all(r['image'].shape==(128,128,3) for r in app.session_state['run']['results'].values())
next(s for s in app.selectbox if s.label=='Chế độ xử lý').set_value('Chuyển sang ảnh xám').run()
assert not app.exception,app.exception
assert app.session_state['work'].ndim==2 and 'run' not in app.session_state
upload_script=f'''
import sys
sys.path.insert(0,{repr(str(SRC))})
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import streamlit as st
import app_ui
from image_io import png
x=np.arange(16*18*3,dtype=np.uint16).reshape(16,18,3)*70
upload=SimpleNamespace(name='test_rgb16.png',getvalue=lambda:png(x))
with patch.object(st,'file_uploader',side_effect=lambda *a,**kw:upload if kw.get('key')=='source_upload' else None):
    app_ui.main()
'''
app=AppTest.from_string(upload_script,default_timeout=60).run()
next(r for r in app.radio if r.label=='Nguồn ảnh').set_value('Tải ảnh của bạn').run()
next(s for s in app.selectbox if s.label=='Vùng ảnh thực hành').set_value('Toàn bộ ảnh').run()
assert not app.exception,app.exception
assert app.session_state['work'].dtype==np.uint16
next(c for c in app.checkbox if c.label=='Ảnh nguồn là ground truth sạch').set_value(True).run()
next(b for b in app.button if b.label=='Tạo nhiễu từ ảnh gốc').click().run()
next(c for c in app.checkbox if c.label=='Ước lượng sigma bằng wavelet').set_value(True).run()
next(s for s in app.multiselect if s.label=='Phương pháp cần chạy').set_value(['NLM tự cài đặt','Mean']).run()
next(b for b in app.button if b.label=='Khử nhiễu và so sánh').click().run()
assert not app.exception,app.exception
assert app.session_state['run']['params']['auto_sigma'] is True
assert all(r['image'].dtype==np.uint16 and r['image'].shape==(16,18,3) for r in app.session_state['run']['results'].values())
print('PASS: gray/RGB uint8/16 PNG and TIFF roundtrip, 8 filters, noise, channel isolation, joint NLM, metrics scaling, alpha, float rejection, color UI, RGB16 upload, automatic sigma, grayscale reset')
