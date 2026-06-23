import httpx

jobs = [
    "7ac8203e-9d3e-4b5a-b8ab-6c01df921ffa",
    "f00a23a8-fb1e-4548-8ae6-4e3d6f5e05ec",
    "2de121b3-1ad7-41f1-ba6b-bb65f7346774",
    "39137b0c-f90c-4dee-90e6-6c559a6bc69e",
    "0e07e3d1-a205-4f70-ad85-21d7fde93076",
    "7d78482b-caec-4cff-8df2-234f6cf46c6a"
]

for job_id in jobs:
    url = f"http://127.0.0.1:8000/api/v1/scan/{job_id}/recommendations"
    try:
        r = httpx.get(url)
        data = r.json()
        print(f"Job ID: {job_id} | Recommendations Count: {len(data)}")
        if len(data) > 0:
            print(f"  First Recommendation Title: {data[0]['title']}")
    except Exception as e:
        print(f"Job ID: {job_id} | Error: {str(e)}")
