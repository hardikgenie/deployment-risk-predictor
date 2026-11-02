import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_recall_fscore_support, average_precision_score, roc_auc_score, confusion_matrix
from sklearn.model_selection import GroupShuffleSplit
import joblib

NUM=['additions','deletions','files_modified','msg_len','num_parents','time_since_last_commit']
CAT=['event','is_merge']
FEATURES=NUM+CAT

def main():
 p=argparse.ArgumentParser();p.add_argument('--csv',required=True);p.add_argument('--out',default='real_model_outputs');p.add_argument('--max-rows',type=int,default=100000);a=p.parse_args()
 out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 use=['repo','commit_sha','conclusion','status','created_at']+FEATURES
 d=pd.read_csv(a.csv,usecols=lambda c:c in use,low_memory=False)
 audit={'total_rows':len(d),'outcome_counts':d.conclusion.fillna('MISSING').value_counts().to_dict()}
 d=d[d.conclusion.isin(['success','failure','passed','failed'])].copy()
 d['label']=d.conclusion.isin(['failure','failed']).astype(int)
 d['date']=pd.to_datetime(d.created_at,utc=True,errors='coerce')
 d=d[d.date.notna() & d.repo.notna() & d.commit_sha.notna()].copy()
 d=d.sort_values('date')
 if len(d)>a.max_rows: d=d.iloc[np.linspace(0,len(d)-1,a.max_rows,dtype=int)].copy()
 for c in NUM:d[c]=pd.to_numeric(d[c],errors='coerce')
 for c in CAT:d[c]=d[c].fillna('unknown').astype(str)
 # Hold out latest 20%, remove train observations sharing repo+commit with test.
 split=int(len(d)*.8);train=d.iloc[:split].copy();test=d.iloc[split:].copy()
 test_keys=set(test.repo.astype(str)+'|'+test.commit_sha.astype(str))
 train=train[~(train.repo.astype(str)+'|'+train.commit_sha.astype(str)).isin(test_keys)]
 prep=ColumnTransformer([('num',Pipeline([('impute',SimpleImputer(strategy='median')),('scale',StandardScaler())]),NUM),('cat',Pipeline([('impute',SimpleImputer(strategy='most_frequent')),('encode',OneHotEncoder(handle_unknown='ignore'))]),CAT)])
 models={'logistic_regression':LogisticRegression(max_iter=600,class_weight='balanced'),'random_forest':RandomForestClassifier(n_estimators=100,max_depth=12,min_samples_leaf=8,class_weight='balanced_subsample',random_state=42,n_jobs=-1)}
 metrics={};best=None;best_ap=-1
 for name,est in models.items():
  pipe=Pipeline([('prep',prep),('model',est)]);pipe.fit(train[FEATURES],train.label)
  prob=pipe.predict_proba(test[FEATURES])[:,1];pred=(prob>=.5).astype(int)
  pr,re,f1,_=precision_recall_fscore_support(test.label,pred,average='binary',zero_division=0)
  ap=average_precision_score(test.label,prob)
  metrics[name]={'precision':float(pr),'recall':float(re),'f1':float(f1),'pr_auc':float(ap),'roc_auc':float(roc_auc_score(test.label,prob)) if test.label.nunique()==2 else None,'confusion_matrix':confusion_matrix(test.label,pred,labels=[0,1]).tolist()}
  if ap>best_ap:best_ap=ap;best=(name,pipe)
 audit.update({'usable_rows_before_sampling':int(len(d)) if len(d)<a.max_rows else 'at least '+str(a.max_rows),'sampled_rows':len(d),'train_rows':len(train),'test_rows':len(test),'train_failure_rate':float(train.label.mean()),'test_failure_rate':float(test.label.mean()),'train_end':str(train.date.max()),'test_start':str(test.date.min()),'features':FEATURES,'caveat':'Target is CI run failure, not production deployment failure. Historical dataset provenance and feature timing require verification.'})
 joblib.dump({'pipeline':best[1],'features':FEATURES,'target':'CI run failure','model_name':best[0]},out/'real_ci_failure_model.joblib')
 (out/'evaluation.json').write_text(json.dumps({'audit':audit,'models':metrics,'selected_model':best[0]},indent=2))
 print(json.dumps({'audit':audit,'models':metrics,'selected_model':best[0]},indent=2))
if __name__=='__main__':main()
