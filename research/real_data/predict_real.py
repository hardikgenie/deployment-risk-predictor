import argparse, json, joblib, pandas as pd
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--model',default='results/real_ci_failure_model.joblib');p.add_argument('--input',required=True,help='JSON object with pre-run features');a=p.parse_args()
b=joblib.load(a.model);x=json.loads(Path(a.input).read_text());row=pd.DataFrame([x]);prob=float(b['pipeline'].predict_proba(row[b['features']])[0,1]);print(json.dumps({'ci_failure_risk_score':round(prob,4),'risk_band':'HIGH' if prob>=.67 else 'MEDIUM' if prob>=.34 else 'LOW','target':b['target'],'model':b['model_name'],'notice':'Research model: CI failure risk, not calibrated deployment-failure probability.'},indent=2))
