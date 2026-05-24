# TikTok KOL Optimizer

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Generate simulated data:
```bash
python data/generator.py
```

3. Start backend (Terminal 1):
```bash
uvicorn backend.main:app --reload
```

4. Start frontend (Terminal 2):
```bash
streamlit run frontend/app.py
```

5. Run comparison experiment and plot:
```bash
python experiments/run_comparison.py
```
