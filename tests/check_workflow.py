"""Integration checks for seeded experiments, exports and UI state."""
import io
import json
import sys
import zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from nlm_lab import noise, metrics, load_image, png, filter_image
from experiment import DEFAULTS, METHODS, benchmark, package
from streamlit.testing.v1 import AppTest

x=np.tile(np.arange(16,dtype=np.uint8)*16,(16,1))
for kind,level in [('Salt and pepper',1.1),('Poisson',0),('Gaussian',-1)]:
    try: noise(x,kind,level,42)
    except ValueError: pass
    else: raise AssertionError('invalid noise not rejected')
p=DEFAULTS.copy(); p.update(patch=3,radius=2)
y=noise(x,'Gaussian',20,42)
results=benchmark(y,METHODS,p,2,True)
payload,rows,comparisons=package(x,y,results,p,dict(kind='Gaussian',level=20,seed=42),True,fiji=x,repeats=2,warmup=True)
with zipfile.ZipFile(io.BytesIO(payload)) as z:
    m=json.loads(z.read('metadata.json'))
    assert len(m['files'])==8 and len(rows)==10 and len(comparisons)==8
    assert 'fiji_result.png' in z.namelist()
    for method,record in results.items():
        saved=load_image(io.BytesIO(z.read(m['files'][method])))
        np.testing.assert_array_equal(saved,record['image'])
        assert metrics(x,saved)==next({k:r[k] for k in ['MSE','PSNR_dB','SSIM']} for r in rows if r['method']==method)
assert all('PSNR_dB' not in r for r in package(x,y,results,p,None,False)[1])

app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'src'/'nlm_lab.py'),default_timeout=120).run()
assert not app.exception,app.exception
assert len(app.tabs)==4
next(b for b in app.button if b.label=='Tạo nhiễu từ ảnh gốc').click().run()
assert not app.exception,app.exception
next(c for c in app.checkbox if c.label=='Ước lượng sigma bằng wavelet').set_value(True).run()
assert not app.exception,app.exception
next(s for s in app.multiselect if s.label=='Phương pháp cần chạy').set_value(['Mean','Median']).run()
next(b for b in app.button if b.label=='Khử nhiễu và so sánh').click().run()
assert not app.exception,app.exception
assert len(app.session_state['run']['results'])==2
assert app.session_state['run']['params']['auto_sigma'] is True
assert np.isfinite(app.session_state['run']['params']['sigma'])
next(s for s in app.slider if s.label=='Hệ số h / sigma').set_value(.6).run()
assert any('cấu hình' in w.value for w in app.warning)
next(b for b in app.button if b.label=='Duplicate ảnh gốc vào ảnh làm việc').click().run()
assert 'run' not in app.session_state
assert not app.exception,app.exception
print('PASS: 8 filters, 2-run benchmark, ZIP pixel/metric consistency, Fiji inclusion, no-ground-truth export, 4-tab UI, noise, run, stale params, reset')
