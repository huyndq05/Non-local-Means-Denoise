"""Check theme contract, redesigned views, crop resets, and no-reference mode."""
import sys
from pathlib import Path
import tomllib
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from streamlit.testing.v1 import AppTest
from ui_theme import STYLES

ROOT=Path(__file__).resolve().parents[1]
config=tomllib.loads((ROOT/'.streamlit/config.toml').read_text(encoding='utf-8'))
theme=config['theme']


def luminance(hex_color):
    rgb=[int(hex_color.lstrip('#')[i:i+2],16)/255 for i in (0,2,4)]
    linear=[c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in rgb]
    return sum(a*b for a,b in zip(linear,[.2126,.7152,.0722]))


def ratio(a,b):
    x,y=sorted([luminance(a),luminance(b)])
    return (y+.05)/(x+.05)


assert ratio(theme['textColor'],theme['backgroundColor'])>=7
assert ratio(theme['textColor'],theme['secondaryBackgroundColor'])>=7
assert ratio(theme['primaryColor'],'#FFFFFF')>=4.5
assert '.stApp{background:#f6f8fb}' not in STYLES
for token in ['--text-color','--background-color','--secondary-background-color','--primary-color']:
    assert f'var({token})' not in STYLES, 'Do not depend on iframe-only theme variables'
import re
assert not re.search(r'background(?:-color)?\s*:',STYLES), 'Native theme must own surface colors'
assert all(value.strip()=='inherit' for value in re.findall(r'(?<![\w-])color\s*:\s*([^;}]+)',STYLES))

app=AppTest.from_file(str(ROOT/'nlm_lab.py'),default_timeout=60).run()
assert not app.exception,app.exception
assert app.session_state['work'].shape[:2]==(256,256)
next(s for s in app.selectbox if s.label=='Vùng ảnh thực hành').set_value('Crop giữa 128 × 128').run()
assert app.session_state['work'].shape[:2]==(128,128)
next(b for b in app.button if b.label=='Tạo nhiễu từ ảnh gốc').click().run()
next(s for s in app.multiselect if s.label=='Phương pháp cần chạy').set_value(['Mean','Median']).run()
next(b for b in app.button if b.label=='Khử nhiễu và so sánh').click().run()
assert not app.exception,app.exception
assert next(s for s in app.selectbox if s.label=='Phương pháp đang xem')
next(r for r in app.radio if r.label=='Cách xem kết quả').set_value('Tất cả phương pháp').run()
assert not app.exception,app.exception
next(c for c in app.checkbox if c.label=='Ảnh nguồn là ground truth sạch').set_value(False).run()
assert not app.exception,app.exception
assert all('PSNR_dB' not in frame.value.columns for frame in app.dataframe)
next(s for s in app.selectbox if s.label=='Vùng ảnh thực hành').set_value('Crop giữa 256 × 256').run()
assert 'run' not in app.session_state
assert 'noise_config' not in app.session_state
assert not app.exception,app.exception
print('PASS: light contrast >=7:1, primary button >=4.5:1, no forced surface colors, crop, focused/gallery views, no-ground-truth mode, source reset')
