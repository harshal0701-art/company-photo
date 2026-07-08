import os
import json
import sys
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

def get_committed_image():
    """Finds the uploaded image path using the GitHub Push Event payload metadata."""
    event_path = os.getenv("GITHUB_EVENT_PATH")
    if not event_path:
        return get_latest_local_image()

    try:
        with open(event_path, 'r') as f:
            event_data = json.load(f)
        
        commits = event_data.get("commits", [])
        changed_files = []
        for commit in commits:
            changed_files.extend(commit.get("added", []))
            changed_files.extend(commit.get("modified", []))
        
        supported_extensions = ('.jpg', '.jpeg', '.png')
        images = [f for f in changed_files if f.startswith("photos/") and f.lower().endswith(supported_extensions)]
        
        if images:
            return images[0]
            
    except Exception as e:
        print(f"Error parsing GitHub Event JSON: {e}")
        
    return get_latest_local_image()

def get_latest_local_image(photo_dir="photos"):
    if not os.path.exists(photo_dir) or not os.listdir(photo_dir):
        print(f"Error: No photos folder found or directory is empty.")
        sys.exit(1)
    supported_extensions = ('.jpg', '.jpeg', '.png')
    files = [os.path.join(photo_dir, f) for f in os.listdir(photo_dir) if f.lower().endswith(supported_extensions)]
    if not files:
        print("Error: No valid images found.")
        sys.exit(1)
    return max(files, key=os.path.getmtime)

def main():
    bucket_name = os.getenv("AWS_S3_BUCKET")
    if not bucket_name:
        print("Error: AWS_S3_BUCKET environment variable is missing.")
        sys.exit(1)

    image_path = get_committed_image()
    if not os.path.exists(image_path):
        print(f"Error: File path '{image_path}' does not exist.")
        sys.exit(1)
        
    file_name = os.path.basename(image_path)
    s3_client = boto3.client('s3')
    rekognition_client = boto3.client('rekognition')

    # Stream file to S3
    try:
        print(f"Uploading '{image_path}' to S3 bucket '{bucket_name}'...")
        s3_client.upload_file(image_path, bucket_name, file_name)
        print("S3 upload successful.")
    except (NoCredentialsError, ClientError) as e:
        print(f"S3 Upload Failed: {e}")
        sys.exit(1)

    # Invoke Amazon Rekognition
    try:
        print("Invoking Amazon Rekognition face detection...")
        response = rekognition_client.detect_faces(
            Image={
                'S3Object': {
                    'Bucket': bucket_name,
                    'Name': file_name
                }
            },
            Attributes=['DEFAULT']
        )
        
        face_details = response.get('FaceDetails', [])
        face_count = len(face_details)
        
        # REQUIRED PRINT OUTPUT
        print("\n==============================")
        print(f"Number of faces: {face_count}")
        for idx, face in enumerate(face_details, start=1):
            print(f"Face #{idx} Confidence: {face.get('Confidence'):.2f}%")
        print("==============================\n")
        
        # REQUIRED SAVE TO JSON
        result_payload = {
            "file_name": file_name,
            "s3_path": f"s3://{bucket_name}/{file_name}",
            "number_of_faces": face_count,
            "face_details": [
                {
                    "face_number": idx,
                    "confidence": round(face.get('Confidence'), 2)
                } for idx, face in enumerate(face_details, start=1)
            ]
        }
        
        with open("result.json", "w") as f:
            json.dump(result_payload, f, indent=4)
        print("Successfully generated and saved result.json.")

    except ClientError as e:
        print(f"Rekognition Processing Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()