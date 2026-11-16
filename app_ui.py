"""Vietnamese NLM teaching lab. Run through nlm_lab.py."""
import hashlib
import io
from pathlib import Path
import numpy as np
import streamlit as st
from skimage.restoration import estimate_sigma
from nlm_lab import load_image, noise, png, metrics, preview, intensity_range
from experiment import METHODS, benchmark, package, csv_bytes
from ui_theme import STYLES, section
from sync_viewer import compare_images

ROOT = Path(__file__).resolve().parent


def reset_work(image):
    st.session_state.work = image.copy()
    for key in ('run', 'sweep', 'noise_config'):
        st.session_state.pop(key, None)


def main():
    st.set_page_config(page_title='NLM Lab • Phòng thực nghiệm', page_icon='🔬', layout='wide')
    st.markdown(STYLES, unsafe_allow_html=True)
    st.markdown('<div class="lab-eyebrow">Xử lý ảnh số · Fiji / ImageJ × Python</div>', unsafe_allow_html=True)
    st.title('Khử nhiễu ảnh bằng Non-Local Means')
    st.markdown('<p class="lab-subtitle">Tạo nhiễu có kiểm soát, tìm hiểu tham số và so sánh chất lượng khôi phục trên cùng một ảnh.</p>', unsafe_allow_html=True)
    with st.sidebar:
        st.markdown('<div class="lab-brand">NLM<span> / Lab</span></div>', unsafe_allow_html=True)
        st.caption('Phòng thực nghiệm xử lý ảnh')
        st.divider()
        section(st, '01', 'Chọn dữ liệu')
        mode = st.radio('Nguồn ảnh', ['Ảnh mẫu trong dự án', 'Tải ảnh của bạn'])
        color_mode=st.selectbox('Chế độ xử lý', ['Giữ màu gốc', 'Chuyển sang ảnh xám'],
                                help='Giữ RGB nếu ảnh có màu. Ảnh xám và dữ liệu 16-bit được giữ đúng độ sâu bit.')
        upload = None
        if mode == 'Ảnh mẫu trong dự án':
            sample_dir=ROOT/'data/clean'
            samples = sorted(sample_dir.glob('*.png'))
            if not samples:
                st.error('Không có ảnh mẫu. Chọn tải ảnh của bạn.'); return
            name = st.selectbox('Ảnh sạch tham chiếu', [p.name for p in samples],
                                format_func=lambda value: Path(value).stem.replace('_', ' '))
            raw = (sample_dir/name).read_bytes()
        else:
            upload = st.file_uploader('Ảnh nguồn · PNG / JPEG / TIFF 8 hoặc 16-bit', type=['png','jpg','jpeg','tif','tiff'], key='source_upload')
            if upload is None:
                st.info('Chọn một ảnh để bắt đầu.'); return
            raw, name = upload.getvalue(), upload.name
        crop = st.selectbox('Vùng ảnh thực hành', ['Crop giữa 256 × 256', 'Crop giữa 128 × 128', 'Toàn bộ ảnh'],
                            help='Crop trước khi sinh nhiễu, không thay đổi tỉ lệ. 256 × 256 giúp chạy nhanh và dùng được tab khảo sát.')
    try:
        original = load_image(io.BytesIO(raw),color=color_mode=='Giữ màu gốc')
    except Exception as exc:
        st.error(str(exc)); return
    if min(original.shape[:2]) < 7:
        st.error('Cần ảnh tối thiểu 7×7 pixel.'); return
    if crop != 'Toàn bộ ảnh':
        side = min(128 if '128' in crop else 256, *original.shape[:2])
        cy, cx = (original.shape[0]-side)//2, (original.shape[1]-side)//2
        original = original[cy:cy+side, cx:cx+side].copy()
        name = f'{name} [crop x={cx}, y={cy}, width={side}, height={side}]'
    if np.prod(original.shape[:2])>1024*1024:
        st.error('Toàn ảnh vượt 1 megapixel. Chọn crop 128 hoặc 256 ở thanh bên.'); return
    source_hash = hashlib.sha256(raw + crop.encode('utf-8') + color_mode.encode('utf-8')).hexdigest()
    if st.session_state.get('source_hash') != source_hash:
        reset_work(original)
        st.session_state.source_hash = source_hash
    with st.sidebar:
        gt = st.checkbox('Ảnh nguồn là ground truth sạch', value=mode=='Ảnh mẫu trong dự án',
                         key='gt_'+source_hash[:12], help='Chỉ bật nếu ảnh này là ảnh sạch mục tiêu. Ảnh nhiễu thực không có ground truth thì không tính metric chất lượng.')
        if st.button('Duplicate ảnh gốc vào ảnh làm việc'):
            reset_work(original)
        st.divider()
        section(st, '02', 'Tạo ảnh nhiễu')
        st.caption('Sigma, h và sigma cường độ dùng thang quy đổi 0–255 cho cả ảnh 8/16-bit. Ví dụ sigma 20 tương ứng khoảng 5140 mức trên ảnh 16-bit.')
        kind = st.selectbox('Mô hình nhiễu', ['Gaussian','Salt and pepper','Poisson'])
        if kind == 'Gaussian':
            level = st.number_input('Sigma nhiễu (mức xám)', 0., 100., 20., help='Độ lệch chuẩn trên thang 0–255. Tăng sigma làm nhiễu mạnh hơn.')
        elif kind == 'Salt and pepper':
            level = st.number_input('Xác suất p', 0., 1., .05, .01, format='%.3f', help='Tổng xác suất thay thế: p/2 thành đen, p/2 thành trắng.')
        else:
            level = st.number_input('Peak Poisson', .1, 10000., 30., help='Số đếm kỳ vọng ở mức trắng. Peak càng nhỏ, nhiễu càng mạnh.')
        seed = st.number_input('Seed tái lập', 0, 2147483647, 42)
        if st.button('Tạo nhiễu từ ảnh gốc'):
            if not gt:
                st.error('Cần xác nhận ảnh sạch trước khi mô phỏng.')
            else:
                reset_work(noise(original, kind, level, seed))
                st.session_state.noise_config = dict(kind=kind, level=level, seed=seed)
        st.divider()
        section(st, '03', 'Điều chỉnh bộ lọc')
        with st.expander('Non-Local Means · tham số chính', expanded=True):
            sigma = st.number_input('Sigma giả định', 0., 100., 20., help='Độ nhiễu Gaussian dùng hiệu chỉnh khoảng cách patch. Khác sigma không gian của Gaussian filter.')
            auto = st.checkbox('Ước lượng sigma bằng wavelet', help='Phù hợp Gaussian. Texture, muối tiêu và Poisson có thể gây thiên lệch. Khác bộ ước lượng Immerkaer của Fiji.')
            factor = st.slider('Hệ số h / sigma', .05, 2., .4, .05, help='Tăng h chấp nhận nhiều patch khác nhau, giảm nhiễu mạnh nhưng dễ mất chi tiết.')
            patch = st.select_slider('Cạnh patch P', [1,3,5,7,9,11], value=5, help='Số pixel mỗi cạnh vùng so sánh. Patch lớn ổn định hơn nhưng có thể trộn cấu trúc.')
            radius = st.slider('Bán kính tìm kiếm r', 1, 20, 5, help='Cạnh cửa sổ là 2r+1. Thời gian tăng xấp xỉ theo bình phương cạnh cửa sổ.')
        with st.expander('Mean, Gaussian, Median, Bilateral'):
            kernel = st.select_slider('Cạnh kernel mean / median', [3,5,7,9], value=3)
            gaussian = st.slider('Gaussian sigma không gian (pixel)', .1, 5., 1.)
            color = st.slider('Bilateral sigma cường độ', 1., 100., 20.)
            spatial = st.slider('Bilateral sigma không gian (pixel)', .5, 10., 3.)
        with st.expander('Cải tiến và đo thời gian'):
            peak = st.number_input('Peak dùng cho Anscombe', .1, 10000., 30., help='Phải trùng peak mô phỏng. Ảnh nhiễu thực cần biết mô hình số đếm.')
            anscombe_h = st.slider('h trong miền Anscombe', .1, 2., .8, .1, help='Miền biến đổi có sigma xấp xỉ 1, không dùng h theo mức xám 0–255.')
            repeats = st.slider('Số lần đo thời gian', 1, 7, 3)
            warmup = st.checkbox('Chạy một lượt làm nóng', value=True)
        st.divider()
        st.caption('Màu giao diện đồng bộ với Streamlit. Đổi sáng / tối tại menu ⋮ → Settings → Theme.')
    work = st.session_state.work
    used_sigma = sigma
    if auto:
        try:
            estimate = float(estimate_sigma(work.astype(float)*255/intensity_range(work),
                                            channel_axis=-1 if work.ndim==3 else None, average_sigmas=True))
            if not np.isfinite(estimate):
                raise ValueError('Ước lượng sigma không hữu hạn.')
            used_sigma = max(0., estimate)
        except (ImportError, ValueError):
            auto = False
            st.warning('Không thể ước lượng sigma tự động. Đang dùng Sigma giả định nhập tay. '
                       'Nếu thiếu PyWavelets, cài lại requirements.txt rồi khởi động lại ứng dụng.')
    params = dict(sigma=used_sigma, h=max(factor*used_sigma,.001), patch=patch, radius=radius,
                  kernel=kernel, gaussian=gaussian, color=color, spatial=spatial,
                  peak=peak, anscombe_h=anscombe_h, auto_sigma=auto)
    st.write('')
    st.caption(f"{'RGB · 3 kênh' if work.ndim==3 else 'Ảnh xám'} · {work.dtype.itemsize*8}-bit · miền gốc 0–{int(intensity_range(work))}. PNG tải xuống giữ độ sâu bit; preview 16-bit được quy đổi cố định về 0–255. Ảnh có alpha được ghép nền trắng.")
    a,b,c,d = st.columns(4)
    a.metric('Kích thước', f'{work.shape[1]} × {work.shape[0]}')
    b.metric('Sigma sử dụng', f'{used_sigma:.2f}')
    c.metric('h mức xám', f'{params["h"]:.2f}')
    d.metric('Cửa sổ tìm kiếm', f'{2*radius+1} × {2*radius+1}')
    tabs = st.tabs(['Thực nghiệm', 'Khảo sát tham số', 'Đối chiếu Fiji', 'Lý thuyết và trợ giúp'])
    config = st.session_state.get('noise_config')
    with tabs[0]:
        section(st, '01', 'Thiết lập lượt chạy')
        control, action = st.columns([3, 1], gap='large', vertical_alignment='bottom')
        with control:
            selected = st.multiselect('Phương pháp cần chạy', METHODS, default=METHODS[:6],
                                      help='Mỗi phương pháp nhận cùng ảnh nhiễu. Hai pipeline cải tiến được chạy và tính thời gian riêng.')
        with action:
            run_clicked = st.button('Khử nhiễu và so sánh', type='primary', width='stretch')
        if 'Anscombe + NLM' in selected:
            st.info('Anscombe cần đúng peak của ảnh Poisson. Biến đổi ngược đại số có thể gây thiên lệch ở peak thấp.')
        if run_clicked:
            if not selected:
                st.error('Chọn ít nhất một phương pháp.')
            elif work.size*(2*radius+1)**2*repeats > 1_500_000_000 and any('NLM' in m for m in selected):
                st.error('Cấu hình quá nặng cho demo. Giảm bán kính, số lần lặp hoặc chọn crop ở thanh bên.')
            else:
                try:
                    with st.status('Đang xử lý cùng ảnh đầu vào…', expanded=True) as progress:
                        st.write(f'{len(selected)} phương pháp · {repeats} lượt đo mỗi phương pháp')
                        results = benchmark(work, selected, params, repeats, warmup)
                        st.session_state.run = dict(results=results, params=params.copy(), repeats=repeats, warmup=warmup)
                        progress.update(label='Đã hoàn tất khử nhiễu', state='complete', expanded=False)
                except Exception as exc:
                    st.error(f'Không xử lý được: {exc}')
        section(st, '02', 'Ảnh đầu vào dùng chung')
        st.caption(name)
        if config:
            label = {'Gaussian': 'Gaussian · sigma', 'Salt and pepper': 'Muối tiêu · p', 'Poisson': 'Poisson · peak'}[config['kind']]
            st.caption(f"{label} = {config['level']:g} · seed {config['seed']} · mọi bộ lọc dùng cùng ảnh này")
        else:
            st.info('Chưa tạo nhiễu. Chọn mô hình và bấm “Tạo nhiễu từ ảnh gốc” ở thanh bên để bắt đầu thí nghiệm.')
        compare_images(original,work,'Ảnh nguồn · '+('ground truth sạch' if gt else 'chưa xác nhận sạch'),
                       'Ảnh làm việc · đầu vào chung',key='inputs_'+source_hash[:16])
        st.caption('Kính lúp đồng bộ: rê chuột để soi, cuộn để phóng to, giữ và kéo để di chuyển trên ảnh bất kỳ.')
        left, right = st.columns(2, gap='large')
        with left:
            st.download_button('Tải ảnh nguồn để đo MSE', png(original), 'source_rgb.png' if original.ndim==3 else 'source_gray.png', 'image/png', width='stretch')
        with right:
            st.download_button('Tải ảnh làm việc để mở trong Fiji', png(work), 'noisy_input.png', 'image/png', width='stretch')
        section(st, '03', 'Kết quả và chất lượng khôi phục')
        run = st.session_state.get('run')
        if run:
            if run['params'] != params or run['repeats'] != repeats or run['warmup'] != warmup:
                st.warning('Bạn đã đổi cấu hình. Kết quả hiện tại thuộc lần chạy trước; bấm chạy lại để cập nhật.')
            _, rows, _ = package(original, work, run['results'], run['params'], config, gt)
            view = st.radio('Cách xem kết quả', ['So sánh từng phương pháp', 'Tất cả phương pháp'], horizontal=True)
            if view == 'So sánh từng phương pháp':
                method = st.selectbox('Phương pháp đang xem', list(run['results']))
                record = run['results'][method]
                compare_images(work,record['image'],'Trước khử nhiễu','Sau khử nhiễu · '+method,
                               key='results_'+source_hash[:16])
                st.caption('Zoom và kéo từ bên trái hoặc bên phải đều đồng bộ. Đổi phương pháp vẫn giữ vùng đang xem khi ảnh đầu vào không đổi. Preview 16-bit dùng cùng thang quy đổi cố định.')
                if gt:
                    score = metrics(original, record['image'])
                    noisy_psnr = metrics(original, work)['PSNR_dB']
                    m1, m2, m3, m4 = st.columns(4)
                    change = score['PSNR_dB'] - noisy_psnr
                    m1.metric('PSNR', f"{score['PSNR_dB']:.2f} dB", f'{change:+.2f} dB so với ảnh nhiễu' if np.isfinite(change) else None)
                    m2.metric('SSIM', f"{score['SSIM']:.4f}")
                    m3.metric('MSE', f"{score['MSE']:.2f}")
                    m4.metric('Thời gian trung vị', f"{record['seconds']:.4f} s")
                st.download_button('Tải ảnh kết quả đang xem', png(record['image']), 'denoised_result.png', 'image/png')
            else:
                for offset in range(0, len(run['results']), 3):
                    grid = st.columns(3, gap='medium')
                    for col, (method, record) in zip(grid, list(run['results'].items())[offset:offset+3]):
                        with col, st.container(border=True):
                            st.markdown('**' + method + '**')
                            st.image(preview(record['image']), clamp=True, width='stretch')
                            st.caption(f"Trung vị {record['seconds']:.4f} s")
            st.markdown('#### Bảng so sánh định lượng')
            st.caption('Metric tính trên dữ liệu xuất đúng 8/16-bit. MSE theo bình phương đơn vị cường độ gốc; PSNR dùng đỉnh 255 hoặc 65535. Với RGB, MSE và SSIM lấy trung bình qua các kênh.')
            st.dataframe(rows, hide_index=True, width='stretch')
            if gt:
                import pandas as pd
                chart = pd.DataFrame(rows).set_index('method')[['PSNR_dB']].replace([np.inf, -np.inf], np.nan)
                st.bar_chart(chart, y_label='PSNR (dB)', color='#087F8C')
            else:
                st.info('Không có ground truth: chỉ xem đầu ra và thời gian, không suy ra PSNR/SSIM chất lượng.')
            export, _, _ = package(original, work, run['results'], run['params'], config, gt, name,
                                   repeats=run['repeats'], warmup=run['warmup'])
            st.download_button('Tải gói kết quả Python', export, 'nlm_python_experiment.zip', 'application/zip', width='stretch')
            st.caption('Để thêm kết quả Fiji vào cùng gói ZIP, chuyển sang tab Đối chiếu Fiji.')
            with st.expander('Chi tiết cấu hình và thời gian từng lượt'):
                st.json(dict(parameters=run['params'], times={k:v['times'] for k,v in run['results'].items()}))
        else:
            st.markdown('<div class="lab-empty">Kết quả sẽ xuất hiện tại đây.<br>Chọn phương pháp phía trên và bấm <strong>Khử nhiễu và so sánh</strong>. Bạn có thể xem trước / sau, chỉ số chất lượng và tải toàn bộ dữ liệu.</div>', unsafe_allow_html=True)
    with tabs[1]:
        st.subheader('Thay một tham số trên cùng ảnh nhiễu')
        st.write('Khảo sát dùng NLM tự cài đặt. Dùng ảnh hiệu chỉnh để chọn cấu hình rồi khóa trước khi đánh giá ảnh test.')
        variable = st.selectbox('Tham số khảo sát', ['h / sigma','Cạnh patch P','Bán kính r'])
        values = {'h / sigma':[.2,.4,.6,.8,1.], 'Cạnh patch P':[3,5,7,9], 'Bán kính r':[2,3,5,7,10]}[variable]
        st.caption(f'Giá trị sẽ chạy: {values}. Mỗi điểm đo một lượt sau làm nóng, chỉ khảo sát chất lượng và xu hướng thời gian.')
        if st.button('Chạy khảo sát'):
            if not gt:
                st.error('Khảo sát chất lượng cần ảnh nguồn sạch và ảnh nhiễu mô phỏng.')
            elif np.prod(work.shape[:2]) > 256*256:
                st.error('Khảo sát trong webapp giới hạn 256×256 pixel. Dùng benchmark CLI cho ảnh lớn.')
            else:
                rows=[]
                with st.spinner('Đang khảo sát...'):
                    for v in values:
                        q=params.copy()
                        q[{'h / sigma':'h','Cạnh patch P':'patch','Bán kính r':'radius'}[variable]]= max(v*used_sigma,.001) if variable=='h / sigma' else v
                        rec=benchmark(work,[METHODS[0]],q,1,True)[METHODS[0]]
                        rows.append(dict(value=v, **metrics(original,rec['image']), seconds=rec['seconds'], **q))
                st.session_state.sweep=dict(variable=variable, rows=rows, params=params.copy())
        if st.session_state.get('sweep'):
            sweep=st.session_state.sweep
            st.caption('Khảo sát đã lưu: '+sweep['variable'])
            st.dataframe(sweep['rows'], hide_index=True)
            import pandas as pd
            st.line_chart(pd.DataFrame(sweep['rows']).set_index('value')[['PSNR_dB']])
            st.download_button('Tải CSV khảo sát',csv_bytes(sweep['rows']),'sweep.csv','text/csv')
    with tabs[2]:
        st.subheader('Cùng PNG đầu vào, kiểm chứng độc lập')
        st.write('1. Tải ảnh nguồn và noisy_input.png ở tab Thực nghiệm. 2. Mở noisy_input trong Fiji, duplicate rồi chạy plugin, giữ đúng RGB/xám và độ sâu bit. 3. Lưu PNG kết quả và nhập dưới đây.')
        st.info('Macro fiji_psnr.ijm hiện chỉ dành cho ảnh xám 8-bit. Không dùng macro đó cho RGB/16-bit. Webapp đo kết quả RGB/16-bit với đúng data range; muốn kiểm chứng trong Fiji cần đo từng kênh và dùng đỉnh 65535 cho 16-bit.')
        st.warning('Smoothing Factor của Fiji không bằng trực tiếp h/sigma. Patch, self weight và xử lý biên có thể khác; MAE giữa đầu ra không phải chất lượng so với ảnh sạch.')
        key=hashlib.sha256(png(work)).hexdigest()[:16]
        fiji_upload=st.file_uploader('Kết quả Fiji · cùng kênh và độ sâu bit',type=['png','tif','tiff'],key='fiji_'+key)
        fc1,fc2,fc3=st.columns(3)
        f_sigma=fc1.number_input('Fiji Sigma',1,200,20)
        f_factor=fc2.number_input('Fiji Smoothing Factor nguyên',1,5,1)
        f_auto=fc3.checkbox('Fiji Auto estimate sigma')
        f_version=st.text_input('Fiji / ImageJ / tên JAR / ghi chú',key='fiji_version')
        fiji=None
        if fiji_upload:
            try:
                fiji=load_image(io.BytesIO(fiji_upload.getvalue()),color=True)
                if fiji.shape!=work.shape or fiji.dtype!=work.dtype:
                    fiji=None
                    raise ValueError('Ảnh Fiji khác kích thước, số kênh hoặc độ sâu bit. Không tự resize hay đổi bit để ép khớp.')
                st.image(preview(fiji),caption='Đầu ra Fiji đã nhập',clamp=True)
            except Exception as exc:
                st.error(str(exc))
        run=st.session_state.get('run')
        if run:
            data,rows,comparisons=package(original,work,run['results'],run['params'],config,gt,name,fiji,
                  dict(sigma=f_sigma,smoothing_factor=f_factor,auto=f_auto,environment=f_version),run['repeats'],run['warmup'])
            if fiji is not None:
                st.dataframe(rows,hide_index=True)
                st.dataframe(comparisons,hide_index=True)
            st.download_button('Tải bộ kết quả PNG CSV JSON',data,'nlm_experiment.zip','application/zip',type='primary')
            st.caption('ZIP gồm ảnh sạch, ảnh nhiễu, đầu ra Python, đầu ra Fiji nếu đã nhập, metrics.csv, metadata.json và so sánh Fiji. Kiểm tra cấu hình Fiji nhập tay khớp thao tác thực.')
        else:
            st.info('Chạy bộ lọc Python để xuất gói thí nghiệm đầy đủ.')
        macro=ROOT/'fiji_psnr.ijm'
        if macro.exists():
            st.download_button('Tải macro MSE và PSNR cho Fiji',macro.read_bytes(),macro.name)
    with tabs[3]:
        st.subheader('Cơ chế Non-Local Means')
        st.latex(r'd(i,j)=\frac{1}{P^2 C}\sum_{k\in K}\sum_{c=1}^{C}(v_c(i+k)-v_c(j+k))^2')
        st.caption('C = 1 cho ảnh xám, C = 3 cho RGB. NLM tự cài tính khoảng cách chung qua các kênh, dùng cùng trọng số cho R, G và B.')
        st.latex(r'q(i,j)=\exp\left[-\frac{\max(d(i,j)-2\sigma^2,0)}{h^2}\right],\quad \hat u(i)=\frac{\sum_{j\in S(i)}q(i,j)v(j)}{\sum_{j\in S(i)}q(i,j)}')
        st.write('P mô tả cấu trúc dùng so sánh. r giới hạn nơi tìm ứng viên. h quyết định mức chấp nhận khác biệt. Sigma dùng bù phần khoảng cách do Gaussian. Bản tự cài giữ self weight bằng 1 và đệm phản chiếu NumPy.')
        st.markdown('''- **Gaussian:** bắt đầu sigma=20, h/sigma=0.4, P=5, r=5 rồi khảo sát.
- **Muối tiêu:** p=0.05, thử Median trước; Median + NLM là nhánh riêng và có thể mất nét.
- **Poisson:** peak=30; sigma cố định chỉ là xấp xỉ. Anscombe cần đúng peak và dùng nghịch đảo đại số có thiên lệch.
- **Mean/Median:** cạnh kernel lớn làm mạnh hơn nhưng xóa chi tiết nhỏ.
- **Gaussian filter:** sigma không gian theo pixel, tăng làm ảnh mờ hơn.
- **Bilateral:** sigma không gian chọn phạm vi, sigma cường độ chọn chênh lệch mức xám được trộn.
- **MSE giảm, PSNR tăng, SSIM gần 1** thường là tốt hơn so với ground truth. Luôn kiểm tra crop và thời gian.
''')
        st.caption('SSIM: cửa sổ đều 7×7, phương sai mẫu, data_range=255 hoặc 65535. RGB dùng trọng số patch NLM chung qua ba kênh; bộ lọc cục bộ không trộn trục kênh. Thời gian chỉ gồm hàm lọc.')
        st.markdown('[Plugin Fiji](https://imagej.net/plugins/non-local-means-denoise/) · [Bài NLM IPOL](https://www.ipol.im/pub/art/2011/bcm_nlm/) · [scikit-image](https://scikit-image.org/docs/stable/api/skimage.restoration.html)')
