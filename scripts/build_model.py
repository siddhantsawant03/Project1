import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.model import build
use_demo='--demo' in sys.argv
m=build(use_demo=use_demo)
print(f'Built FP&A model: {len(m):,} rows | {m.month.min().date()} to {m.month.max().date()} | demo={use_demo}')
