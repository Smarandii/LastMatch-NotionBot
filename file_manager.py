import requests
from pathlib import Path
from os import remove
from glob import glob


class FileManager:
    def __init__(self, token, downloaded_files_folder_name="download"):
        self.api_token = token
        self.downloaded_files_folder_name = downloaded_files_folder_name
        self.base_url = f"http://0.0.0.0:8081/bot{self.api_token}"

    def upload_file(self, chat_id, file_path):
        file_size = (Path(file_path).stat().st_size / 1024) / 1024
        print(f"sending {file_path} with size: {file_size} mb")
        url = f'{self.base_url}/sendDocument?chat_id={chat_id}'
        r = requests.post(url, files={"document": open(file_path, 'rb')})  # note: files, not data
        if r.status_code == 200:
            print(f"sent {file_path} with size: {file_size} mb")
        else:
            url = f'{self.base_url}/sendMessage'
            r = requests.post(url, json={"text": f"{file_path.replace(f'download/{chat_id}', '')} can not be sent",
                                         "chat_id": chat_id},)
        remove(file_path)

    def delete_downloaded_files(self, tg_id):
        for file in glob(f"{self.downloaded_files_folder_name}/{tg_id}/*"):
            remove(file)

    def get_downloaded_files(self, tg_id):
        return glob(f"{self.downloaded_files_folder_name}/{tg_id}/*")
