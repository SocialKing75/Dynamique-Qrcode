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
            # Nouveau défaut sans espaces
            folder_path = os.getenv("DROPBOX_FOLDER_PATH", "/Dossier-test-qrcode")
            if folder_path in ["", "/", "."]: folder_path = ""
            elif folder_path and not folder_path.startswith("/"): folder_path = "/" + folder_path

            import logging
            logger = logging.getLogger(__name__)
            
            try:
                return self.dbx.files_list_folder(folder_path, recursive=True)
            except Exception as e:
                if "not_found" in str(e).lower() and folder_path != "":
                    return self.dbx.files_list_folder("", recursive=True)
                raise e

    def find_file_globally(self, filename: str):
        """
        Robustly find a file by name, handling pagination and searching root if needed.
        """
        if not self.dbx:
            raise Exception("Dropbox client not configured")
        
        # 1. Try search API first (faster)
        try:
            res = self.dbx.files_search_v2(filename)
            for match in res.matches:
                metadata = match.metadata.get_metadata()
                if isinstance(metadata, dropbox.files.FileMetadata) and metadata.name.lower() == filename.lower():
                    return metadata
        except Exception:
            pass # Fallback to manual list

        # 2. Manual list with pagination
        paths_to_try = [os.getenv("DROPBOX_FOLDER_PATH", "/Dossier-test-qrcode"), ""]
        for p in paths_to_try:
            if p in ["/", "."]: p = ""
            try:
                res = self.dbx.files_list_folder(p, recursive=True)
                while True:
                    for entry in res.entries:
                        if isinstance(entry, dropbox.files.FileMetadata) and entry.name.lower() == filename.lower():
                            return entry
                    if not res.has_more:
                        break
                    res = self.dbx.files_list_folder_continue(res.cursor)
            except Exception:
                continue
        return None
