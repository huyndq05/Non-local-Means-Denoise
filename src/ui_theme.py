"""Native-theme-aware styles: no fixed light surfaces with inherited dark text."""

STYLES = '''
<style>
/* Leave foregrounds/surfaces to Streamlit's native theme. Its main frontend
   does not expose component iframe CSS variables in every release. */
[data-testid="stAppViewContainer"] {
  --lab-line: rgba(127, 127, 127, .28);
}
.block-container { max-width: 1540px; padding: 2.2rem 2.8rem 3rem; }
[data-testid="stSidebar"] { border-right: 1px solid var(--lab-line); }
[data-testid="stSidebar"] > div:first-child { padding-top: 1.5rem; }
h1, h2, h3, h4 { letter-spacing: -0.025em; }
h1 { font-size: clamp(1.9rem, 3vw, 2.8rem) !important; line-height: 1.18 !important; }
h2 { font-size: 1.35rem !important; }
h3 { font-size: 1.1rem !important; }
[data-testid="stWidgetLabel"] p { font-weight: 550; }
[data-testid="stMetric"] {
  border: 1px solid var(--lab-line);
  border-radius: 12px;
  padding: 15px 18px;
}
[data-testid="stMetricValue"] { font-size: 1.65rem; font-weight: 650; }
[data-testid="stVerticalBlockBorderWrapper"] > div {
  border-color: var(--lab-line) !important;
  border-radius: 14px;
}
[data-baseweb="tab-list"] {
  gap: 1.5rem; border-bottom: 1px solid var(--lab-line); margin: 1rem 0 1.3rem;
}
[data-baseweb="tab"] { font-size: .95rem; padding: .8rem .15rem; height: auto; }
[data-testid="stButton"] button, [data-testid="stDownloadButton"] button {
  min-height: 42px; border-radius: 9px; font-weight: 600;
}
[data-testid="stButton"] button:focus-visible,
[data-testid="stDownloadButton"] button:focus-visible {
  outline: 3px solid currentColor; outline-offset: 3px;
}
[data-testid="stImage"] img { border-radius: 9px; }
[data-testid="stExpander"] { border-color: var(--lab-line); border-radius: 10px; }
.lab-brand {
  color: inherit; font-size: 1.7rem; font-weight: 800;
  letter-spacing: -.055em; margin-bottom: .2rem;
}
.lab-brand span { font-weight: 400; }
.lab-eyebrow {
  color: inherit; font-size: .72rem; letter-spacing: .13em;
  font-weight: 700; text-transform: uppercase; margin-bottom: .6rem;
}
.lab-subtitle { color: inherit; font-size: 1rem; max-width: 850px; line-height: 1.7; }
.lab-section { color: inherit; font-size: 1.02rem; font-weight: 700; margin: .6rem 0 .8rem; }
.lab-section span { margin-right: .55rem; font-size: .8rem; }
.lab-empty {
  color: inherit;
  border: 1px dashed var(--lab-line); border-radius: 12px;
  padding: 1.6rem 1.8rem; line-height: 1.8; margin-top: .8rem;
}
@media (max-width: 850px) {
  .block-container { padding: 1.4rem 1rem 2rem; }
  [data-baseweb="tab-list"] { gap: .8rem; overflow-x: auto; }
  [data-baseweb="tab"] { white-space: nowrap; font-size: .85rem; }
  [data-testid="stMetric"] { padding: 10px; }
  [data-testid="stMetricValue"] { font-size: 1.25rem; }
}
</style>
'''


def section(st, number, title):
    # Only authored, static labels should be passed here.
    st.markdown(f'<div class="lab-section"><span>{number}</span>{title}</div>', unsafe_allow_html=True)
