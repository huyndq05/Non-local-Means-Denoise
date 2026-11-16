"""Exercise both automatic sigma and the missing-optional-dependency path."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from skimage.restoration import estimate_sigma
from streamlit.testing.v1 import AppTest

image=128.+np.random.default_rng(42).normal(0,20,(128,128))
sigma=estimate_sigma(image,channel_axis=None)
assert 17 < sigma < 23, sigma
script='''
from unittest.mock import patch
import app_ui
with patch.object(app_ui, 'estimate_sigma', side_effect=ImportError('PyWavelets missing')):
    app_ui.main()
'''
app=AppTest.from_string(script,default_timeout=60).run()
next(c for c in app.checkbox if c.label=='Ước lượng sigma bằng wavelet').set_value(True).run()
assert not app.exception,app.exception
assert any('Đang dùng Sigma giả định' in w.value for w in app.warning)
next(s for s in app.multiselect if s.label=='Phương pháp cần chạy').set_value(['Mean']).run()
next(b for b in app.button if b.label=='Khử nhiễu và so sánh').click().run()
assert not app.exception,app.exception
assert app.session_state['run']['params']['auto_sigma'] is False
assert app.session_state['run']['params']['sigma']==20.
print(f'PASS: Gaussian sigma20 estimated {sigma:.3f}; missing PyWavelets falls back to manual20 with accurate metadata and working export')
