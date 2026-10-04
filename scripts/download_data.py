from pathlib import Path
import requests

URL = 'https://zenodo.org/records/22206988/files/sapajaykumar/sap-fpa-dataset-v1.1.0.zip?download=1'
OUT = Path(__file__).resolve().parents[1] / 'data' / 'raw' / 'sap-fpa-dataset-v1.1.0.zip'
OUT.parent.mkdir(parents=True, exist_ok=True)
print('Downloading public FP&A dataset...')
r = requests.get(URL, timeout=120, stream=True)
r.raise_for_status()
with OUT.open('wb') as f:
    for chunk in r.iter_content(chunk_size=1024*1024):
        if chunk: f.write(chunk)
print(f'Saved: {OUT}')
print('Next: python scripts/build_model.py')
