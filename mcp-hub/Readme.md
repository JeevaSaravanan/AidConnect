uvicorn api_server:app --host 127.0.0.1 --port 8000


curl -sS http://127.0.0.1:8000/health | jq .



curl -sS -X POST http://127.0.0.1:8000/weather \
  -H "Content-Type: application/json" \
  -d '{"city":"Washington, DC"}' | jq .



  curl -sS -X POST http://127.0.0.1:8000/disaster_plan \
  -H "Content-Type: application/json" \
  -d '{"city":"Washington, DC", "hazard":"flood"}' | jq .


  curl -sS -X POST http://127.0.0.1:8000/arcgis_query \
  -H "Content-Type: application/json" \
  -d '{"data_api_url":"https://hub.arcgis.com/datasets/YOUR_DATASET_ID/api","where":"1=1","limit":5}' | jq .


  curl -sS -X POST http://127.0.0.1:8000/fema_query \
  -H "Content-Type: application/json" \
  -d '{"dataset":"DisasterDeclarationsSummaries","filter":"state eq \"DC\"","top":5}' | jq .