import os
from typing import List, Dict

import boto3

from botocore.exceptions import ClientError
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

class S3Service:
    def __init__(self, logger=logger, aws_access_key_id=None, aws_secret_access_key=None, aws_region=None):
        self.logger = logger

        self.aws_access_key_id = aws_access_key_id or os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_access_key = aws_secret_access_key or os.getenv('AWS_SECRET_ACCESS_KEY')

        missing = []
        if not self.aws_access_key_id:
            missing.append('AWS_ACCESS_KEY_ID')
        if not self.aws_secret_access_key:
            missing.append('AWS_SECRET_ACCESS_KEY')
        if missing:
            raise EnvironmentError(f"Variáveis de ambiente faltando: {', '.join(missing)}")

        self.client = boto3.client(
            's3',
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
        )

    def upload_object(self, bucket, file_path, object_name=None):
        if object_name is None:
            object_name = file_path

        try:
            response = self.client.upload_file(file_path, bucket, object_name)
        except ClientError as e:
            self.logger.error(e)
            return False

        return True

    def upload_objects(self, bucket, files: List[Dict[str, str]]):
        try:
            for file in files:
                file_path = file['path']
                object_name = file.get('name', file_path)
                if not self.upload_object(bucket, file_path, object_name):
                    return False
        except Exception as e:
            self.logger.error(f"Erro ao fazer upload de múltiplos arquivos: {e}")
            return False
        return True

    def download_object(self, bucket, object_name, file_path):
        try:
            self.client.download_file(bucket, object_name, file_path)
        except ClientError as e:
            self.logger.error(e)
            return False

        return True

    def listar_diretorios(self, bucket: str, prefixo: str = '') -> List[str]:
        try:
            response = self.client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefixo,
                Delimiter='/'
            )
            diretorios = response.get('CommonPrefixes', [])
            return [d['Prefix'] for d in diretorios]
        except ClientError as e:
            self.logger.error(f"Erro ao listar diretórios: {e}")
            return []


#if __name__ == "__main__":
#    s3 = S3Service()
#
#    sucesso = s3.listar_diretorios(bucket='agir-bucket')
#    print(sucesso)
#
#    sucesso = s3.upload_object(
#        bucket='agir-bucket',
#        object_name='lara-config/portal.txt',
#        file_path='/home/yaba/agir-unb/portal.txt'
#    )
#    sucesso = s3.download_object(
#        bucket='agir-bucket',
#        object_name='lara-config/orgaos_gdf_links.json',
#        file_path='/home/yaba/agir-unb/orgaos_gdf_links.json'
#    )