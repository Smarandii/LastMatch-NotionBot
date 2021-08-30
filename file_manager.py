import requests
from pathlib import Path
from os import remove
from glob import glob


class FileManager:
    def __init__(self, token, downloaded_files_folder_name="download"):
        self.api_token = token
        self.downloaded_files_folder_name = downloaded_files_folder_name
        self.base_url = f"http://0.0.0.0:8081/bot{self.api_token}"

    @staticmethod
    def __get_file_name(file_path, chat_id):
        return file_path.replace(f'download/{chat_id}/', '')

    @staticmethod
    def __get_file_size(file_path):
        return (Path(file_path).stat().st_size / 1024) / 1024

    def __send_message(self, chat_id, text):
        url = f'{self.base_url}/sendMessage'
        r = requests.post(url, json={"text": text,
                                     "chat_id": chat_id}, )

    def __send_document(self, chat_id, file_path):
        file_name = self.__get_file_name(file_path, chat_id)
        url = f'{self.base_url}/sendDocument?chat_id={chat_id}'
        r = requests.post(url, files={"document": open(file_path, 'rb')})  # note: files, not data
        if r.status_code == 200:
            print(f"sent {file_path}")
        else:
            self.__send_message(chat_id, text=f"{file_name} can not be sent")

    def upload_file(self, chat_id, file_path):
        file_size = self.__get_file_size(file_path)
        file_name = self.__get_file_name(file_path, chat_id)
        print(f"sending {file_path} with size: {file_size} mb")
        self.__send_message(chat_id, text=f"Отправляю {file_name} с размером: {file_size} mb.")
        self.__send_document(chat_id, file_path)
        remove(file_path)

    def delete_downloaded_files(self, tg_id):
        for file in glob(f"{self.downloaded_files_folder_name}/{tg_id}/*"):
            remove(file)

    def get_downloaded_files(self, tg_id):
        return glob(f"{self.downloaded_files_folder_name}/{tg_id}/*")
