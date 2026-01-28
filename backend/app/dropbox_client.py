import dropbox
from dropbox.exceptions import AuthError
import os
from typing import Optional

class DropboxClient:
    def __init__(self):
        self.app_key = (os.getenv("DROPBOX_APP_KEY") or "").strip()
        self.app_secret = (os.getenv("DROPBOX_APP_SECRET") or "").strip()
        self.refresh_token = (os.getenv("DROPBOX_REFRESH_TOKEN") or "").strip()
        self.dbx = None
        
        if self.app_key and self.app_secret and self.refresh_token:
            self.dbx = dropbox.Dropbox(
                oauth2_refresh_token=self.refresh_token,
                app_key=self.app_key,
                app_secret=self.app_secret
            )

    def is_configured(self) -> bool:
        return self.dbx is not None

    def download_file(self, dropbox_path: str, local_path: str):
        if not self.dbx:
            raise Exception("Dropbox client not configured")
        
        with open(local_path, "wb") as f:
            metadata, res = self.dbx.files_download(path=dropbox_path)
            f.write(res.content)
        return metadata

    def upload_file(self, local_path: str, dropbox_path: str):
        if not self.dbx:
            raise Exception("Dropbox client not configured")
        
        with open(local_path, "rb") as f:
            self.dbx.files_upload(f.read(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)

    def get_file_metadata(self, dropbox_path: str):
        if not self.dbx:
            raise Exception("Dropbox client not configured")
        return self.dbx.files_get_metadata(dropbox_path)

    def list_folder_changes(self, cursor: Optional[str] = None):
        if not self.dbx:
            raise Exception("Dropbox client not configured")
        
        if cursor:
            return self.dbx.files_list_folder_continue(cursor)
        else:
            folder_path = os.getenv("DROPBOX_FOLDER_PATH", "/Dossier test qrcode")
            # Dropbox paths should be empty string for root, otherwise start with /
            if folder_path in ["", "/", "."]:
                folder_path = ""
            elif folder_path and not folder_path.startswith("/"):
                folder_path = "/" + folder_path
            
            return self.dbx.files_list_folder(folder_path, recursive=True)
