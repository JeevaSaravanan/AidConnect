import csv, json
FIELDS = [
    "resources_offered","location","details","posted_by",
    "contact_method","source_platform","source_post_id",
    "post_time","availability_window","skills","capacity_notes",
    "latitude","longitude","state","city"
]
with open("people_volunteers.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader()
open("people_volunteers.jsonl","w").close()
open("people_volunteers_rag.jsonl","w").close()
print("Created empty volunteer schema files: people_volunteers.csv, people_volunteers.jsonl, people_volunteers_rag.jsonl")
