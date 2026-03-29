
import oss2
import os

# 明文配置
OSS_ENDPOINT = 'https://oss-cn-beijing.aliyuncs.com'
OSS_REGION = 'cn-beijing'
OSS_BUCKET_NAME = 'experience-tree'
# 这两个是敏感信息，需要通过环境变量或安全配置管理工具来加载，而不是直接写在代码中
OSS_ACCESS_KEY_ID = os.getenv('OSS_ACCESS_KEY_ID', 'your-access-key-id')
OSS_ACCESS_KEY_SECRET = os.getenv('OSS_ACCESS_KEY_SECRET', 'your-access-key-secret')

class OSSUtil:
    @staticmethod
    def upload(file_bytes: bytes, file_name: str) -> str:
        """
        上传文件到阿里云OSS，返回公网访问URL。
        """
        auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
        bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)
        result = bucket.put_object(file_name, file_bytes)
        print("ETag:", result.etag)
        print("RequestId:", result.request_id)
        print("Status:", result.status)
        url = f"https://{OSS_BUCKET_NAME}.{OSS_ENDPOINT.replace('https://', '')}/{file_name}"
        return url

    @staticmethod
    def generate_signed_url(file_name: str, expires: int = 3600) -> str:
        """
        生成带有效期的签名URL，默认1小时。
        """
        auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
        bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)
        return bucket.sign_url('GET', file_name, expires)
