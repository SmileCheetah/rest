# Heat Risk Score MVP

This pipeline predicts only a 0-100 heat-related rest risk score. Route
selection and Cooling Spot selection remain separate responsibilities.

## Pipeline

`heat-stress guidance -> MVP labeling rule -> synthetic data -> XGBRegressor -> Heat Risk Score -> route optimizer`

The initial label is an engineering MVP policy:

- WBGT: 50 points
- continuous exposure: 25 points
- next travel: 10 points
- time since rest: 10 points
- Cooling Spot distance: 5 points

The policy is informed by heat-stress guidance but is not an official NIOSH or
OSHA 0-100 score. The model is trained on synthetic labels, so its evaluation
only measures how well it reproduces this policy. Production thresholds and
weights must be validated against real support-worker rest, fatigue, and
operation data.

## Run

```powershell
cd backend
python -m pip install -r requirements.txt
python scripts/train_heat_risk.py
```

Outputs:

- `data/synthetic_heat_risk.csv`
- `artifacts/heat-risk-model/heat_risk_model.json`
- `artifacts/heat-risk-model/heat_risk_metadata.json`
- `artifacts/heat-risk-model/example_scenarios.json`

Use `load_model()` and `predict_heat_risk()` from `app.ml.heat_risk` at an API
boundary. The prediction function returns only `heat_risk_score` and
`risk_level`; it does not generate a route.
