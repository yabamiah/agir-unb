import os
from typing import List, Dict

import boto3

from botocore.exceptions import ClientError
from dotenv import load_dotenv
from loguru import logger
from werkzeug.wsgi import responder

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
            self.client.upload_file(file_path, bucket, object_name)
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

    def download_object_by_directory(self, bucket, directory, file_path):
        try:
            objects_key = self.listar_objetos(bucket, directory)

            if not objects_key:
                self.logger.error(f"Nenhum arquivo encontrado no diretório: {directory}")
                return False

            for object_key in objects_key:
                base_name = os.path.basename(object_key)
                destination_path = os.path.join(file_path, base_name)

                self.logger.info(f"Baixando arquivo: {base_name} -> {destination_path}")
                self.download_object(
                    bucket=bucket,
                    object_name=object_key,
                    file_path=destination_path
                )

            return True
        except ClientError as e:
            self.logger.error(e)
            return False

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

    def listar_objetos(self, bucket: str, prefixo: str = ''):
        try:
            if prefixo and not prefixo.endswith('/'):
                prefixo += '/'

            response = self.client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefixo
            )

            objetos = response.get('Contents', [])
            return [objeto['Key'] for objeto in objetos if not objeto['Key'].endswith('/')]

        except ClientError as e:
            self.logger.error(f"Erro ao listar objetos: {e}")
            return []

    def object_exists(self, bucket, object_name):
        try:
            self.client.head_object(Bucket=bucket, Key=object_name)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            else:
                self.logger.error(f"Erro ao checar o objeto: {object_name} no buclet {bucket}: {e}")
                raise

#if __name__ == "__main__":
#    s3 = S3Service()
#
#    sucesso = s3.listar_diretorios(bucket='agir-bucket')
#    print("Listagem diretorios:", sucesso)
#
#    sucesso = s3.listar_objetos(bucket='agir-bucket', prefixo='lara-config/')
#    print(sucesso)
#
    #base_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
    #docs_path = os.path.join(base_dir, 'data', 'dani', 'docs', 'input')
    #sucesso = s3.download_object_by_directory('agir-bucket', 'lara-config/', docs_path)
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