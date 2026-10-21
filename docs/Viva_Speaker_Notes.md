# 10-minute Mid-Semester Viva — speaker notes

Target duration: about 8.5–9 minutes, leaving a small buffer for transitions and questions. These are prompts; explain naturally rather than reading word-for-word.

## Slide 1 — Title (about 25 seconds)
Good morning. My dissertation is titled “Design and Development of an AI-Driven Intelligent CI/CD Pipeline for Predictive Deployment Risk Analysis.” The work investigates whether software-delivery signals available before a deployment can help identify risky releases earlier, without removing existing CI/CD controls.

## Slide 2 — Problem and research question (about 70 seconds)
Modern pipelines automate building, tests and quality/security checks, but fixed gates only evaluate the conditions configured into them. Risk may depend on several signals together, including the size of a change, test outcomes, scan findings, retries and previous deployment behaviour. The main research question is whether a predictive layer adds useful information over the conventional pipeline. The goal is decision support, not claiming that every release can be classified perfectly or approved autonomously.

## Slide 3 — Literature review and gap (about 70 seconds)
Continuous Delivery provides the foundation for a repeatable baseline workflow. Accelerate and DORA provide ways to measure delivery and deployment instability. Sculley and colleagues explain that machine-learning systems bring their own data and operational debt, so the model itself must be handled carefully. Chen and Guestrin's XGBoost paper motivates gradient-boosted trees as one candidate for tabular data. The research question is framed as an empirical test: any added predictive value needs to be demonstrated through a fair comparison rather than assumed.

## Slide 4 — Architecture (about 75 seconds)
The proposed flow begins with source control and a CI workflow, then runs the usual build, tests, and quality/security gates. A feature builder extracts signals available at that point. A model estimates a risk probability and translates it into a risk band. A high-risk result can request human review or additional validation; a lower prediction does not bypass established gates. The current code is a local prototype and has not yet been integrated into a real deployment or AKS environment.

## Slide 5 — Methodology and data (about 85 seconds)
First I need an operational definition of a risky deployment, such as a deployment-related failure, rollback or a pre-defined failure criterion. Each record should be tied to a pipeline run and timestamp. Inputs can include change size, test results, code-quality/security findings, retries and recent history. Only data available before the decision point can be used as a feature. The actual outcome is used as a label for evaluation, not as an input for predicting the same run. A conventional baseline will be compared with an AI-assisted pipeline. Candidate models include Logistic Regression, Random Forest and XGBoost, with the final choice determined by the data and the evaluation.

## Slide 6 — Prototype screenshot (about 65 seconds)
This is the initial local proof-of-concept. It has a browser-based form with eleven candidate features, a FastAPI endpoint, a Random Forest demo model, a risk probability/category and review prompts. The API tests verify basic request and response behaviour. The screen explicitly says that the model is trained on synthetic data. The displayed seven-percent score is just a software demonstration: it is not evidence of model accuracy, it is not trained on validated deployment outcomes, and it must not be quoted as a dissertation result.

## Slide 7 — Status and evaluation (about 75 seconds)
The defined work includes the research question, objectives, architecture, feature schema, proposed labels and evaluation plan. The starter prototype is now prepared, but it still requires local verification and integration with a real or controlled CI/CD workflow. Pending work includes dataset collection and validation, model comparison, integration before promotion, and controlled experiments. Evaluation will consider precision, recall, F1 and appropriate AUC metrics, along with pipeline overhead, review rate and false positives/false negatives. Accuracy alone would be insufficient, especially if risky deployments are relatively rare.

## Slide 8 — Remaining work and contribution (about 55 seconds)
The remaining stages are to establish the baseline and data schema, collect labelled executions, compare models, integrate the risk advisory stage, and evaluate it against the baseline before writing the results. The expected contribution is a reproducible integration pattern and a quantitative assessment of predictive usefulness, operating cost and limitations. At this stage, no claim is being made that the AI layer improves deployment outcomes; the experiments will determine that conclusion. Thank you.

## Before the viva

- Open the PPT and run the prototype from VS Code at least once before presenting it.
- Do not say the prototype is deployed to AKS or integrated into a production pipeline; it currently runs locally.
- Do not cite the demo score or synthetic training metrics as research results.
- Be prepared to explain the difference between a model input feature and a deployment outcome label, and how data leakage will be prevented.
- Update the “completed/pending” slide if your actual progress changes before the session.
