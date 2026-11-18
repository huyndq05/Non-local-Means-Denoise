$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
if (!(Test-Path '.venv/Scripts/python.exe')) {
 throw 'Chua co moi truong Python. Xem README.md de cai dat.'
}
& '.venv/Scripts/python.exe' -m streamlit run src/nlm_lab.py --server.address 127.0.0.1 --browser.gatherUsageStats false
