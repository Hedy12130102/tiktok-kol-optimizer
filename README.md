# TikTok KOL Optimizer

## 快速启动

1. 安装依赖:
```bash
pip install -r requirements.txt
```

2. 生成模拟数据:
```bash
python data/generator.py
```

3. 启动后端 (Terminal 1):
```bash
uvicorn backend.main:app --reload
```

4. 启动前端 (Terminal 2):
```bash
streamlit run frontend/app.py
```

5. 跑对比实验出图:
```bash
python experiments/run_comparison.py
```
