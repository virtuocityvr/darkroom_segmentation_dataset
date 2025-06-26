from src.utils.httpHelper import getStagingCapture
from src.utils.parse_access_token import get_access_token_staging
import json

if __name__ == "__main__":
    capture_id = "683f139fe816660a5784c0a5"
    staging_auth_token = get_access_token_staging()
    response = getStagingCapture(capture_id, staging_auth_token)
    print(response.json())
    with open("new_capture_with_pose.json", "w") as f:
        json.dump(response.json(), f)
