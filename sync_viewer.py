"""Local Streamlit component for two images sharing a pixel viewport."""
import base64
from pathlib import Path
import streamlit.components.v1 as components
from image_io import png, preview

_component = components.declare_component('nlm_sync_viewer', path=str(Path(__file__).parent/'viewer_component'))


def compare_images(left, right, left_title, right_title, key):
    if left.shape[:2]!=right.shape[:2]:
        raise ValueError('Hai ảnh so sánh cần cùng chiều rộng và chiều cao.')
    def data_url(image):
        return 'data:image/png;base64,'+base64.b64encode(png(preview(image))).decode('ascii')
    return _component(left=data_url(left), right=data_url(right),
                      left_title=left_title, right_title=right_title,
                      image_width=left.shape[1], image_height=left.shape[0],
                      key=key, default=None)
