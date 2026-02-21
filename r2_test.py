import boto3

ACCOUNT_ID = "##"
ACCESS_KEY = "##"
SECRET_KEY = "##"

s3 = boto3.client(
    service_name="s3",
    endpoint_url=f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
)

# Test upload
response = s3.put_object(
    Bucket="infinitecloud",
    Key="test.txt",
    Body="Merhaba R2!"
)

print("Upload başarılı 🚀")