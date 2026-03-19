import boto3,os
from dotenv import load_dotenv
try:
    load_dotenv(r"C:\Users\Mehmet Serdar EREN\Desktop\orasu2v.txt")
except:
    pass
s3 = boto3.client(
    service_name="s3",
    endpoint_url=f"https://{os.getenv('ACCOUNT_ID')}.r2.cloudflarestorage.com",
    aws_access_key_id=os.getenv("ACCESS_KEY"),
    aws_secret_access_key=os.getenv("SECRET_KEY"),
    region_name="auto"
)