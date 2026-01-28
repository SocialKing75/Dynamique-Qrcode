from fastapi import APIRouter, Request, HTTPException, Body
from fastapi.responses import JSONResponse
from .dropbox_client import DropboxClient
from . import models, schemas
from .utils import generate_slug
from .pdf_utils import add_qr_to_pdf
import os
import tempfile
import logging
import dropbox

router = APIRouter(prefix="/api/automation", tags=["automation"])
dbx_client = DropboxClient()
logger = logging.getLogger(__name__)

VERSION = "2026-01-28-1645"

@router.get("/debug")
async def debug_automation():
    """Diagnostic pour vérifier la config et la version."""
    def get_token_info(key):
        val = os.getenv(key, "").strip()
        if not val: return "missing"
        return f"set (prefix: {val[:10]}..., len: {len(val)})"

    config = {
        "version": VERSION,
        "DROPBOX_APP_KEY": get_token_info("DROPBOX_APP_KEY"),
        "DROPBOX_REFRESH_TOKEN": get_token_info("DROPBOX_REFRESH_TOKEN"),
        "DROPBOX_FOLDER_PATH": os.getenv("DROPBOX_FOLDER_PATH", "not set (using Dossier-test-qrcode default)"),
        "is_client_initialized": dbx_client.is_configured(),
        "folder_listing": []
    }
    
    if dbx_client.is_configured():
        try:
            res = dbx_client.list_folder_changes()
            config["folder_listing"] = [e.name for e in res.entries[:10]]
            config["total_found"] = len(res.entries)
        except Exception as e:
            config["error"] = str(e)
    return config

@router.post("/manual-process")
async def manual_process_pdf(data: dict = Body(...)):
    """
    Manually trigger PDF processing from a filename.
    """
    filename = data.get("filename")
    if not filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    if not dbx_client.is_configured():
        raise HTTPException(status_code=500, detail="Dropbox not configured")

    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"

    logger.info(f"Manual request to process: {filename}")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "output.pdf")
        
        try:
            # 1. robust search
            target_entry = dbx_client.find_file_globally(filename)
            
            if not target_entry:
                configured_path = os.getenv("DROPBOX_FOLDER_PATH", "non défini (scan racine)")
                raise HTTPException(status_code=404, detail=f"Fichier '{filename}' non trouvé. (Dossier configuré: {configured_path})")

            # 2. Download
            dbx_client.download_file(target_entry.path_lower, input_path)
            
            # 3. Generate Dynamic QR Code in DB
            slug = generate_slug(7)
            while await models.QRCode.find_one(models.QRCode.slug == slug):
                slug = generate_slug(7)
            
            base_url = os.getenv("BASE_URL", "https://your-site.vercel.app")
            redirect_target = f"{base_url}/info/{slug}"
            
            q = models.QRCode(
                slug=slug,
                title=f"Manual process: {target_entry.name}",
                content=redirect_target,
                is_dynamic=True
            )
            await q.insert()
            
            # 4. Preparation of QR Configs
            dynamic_qr_url = f"{base_url}/q/{slug}"
            qr_configs = [
                {'content': dynamic_qr_url, 'x': 450, 'y': 20, 'size': 80}
            ]
            
            # 5. Overlay QR codes
            add_qr_to_pdf(input_path, output_path, qr_configs)
            
            # 6. Upload back to Dropbox finalized folder
            final_dir = os.path.dirname(target_entry.path_lower)
            if final_dir == "/" or not final_dir: final_dir = ""
            finalized_path = f"{final_dir}/finalized/{target_entry.name}"
            
            dbx_client.upload_file(output_path, finalized_path)
            
            # 7. Get a direct download link for the final PDF
            try:
                # Attempt to get existing link
                links = dbx_client.dbx.sharing_list_shared_links(path=finalized_path, direct_only=True).links
                if links:
                    download_url = links[0].url.replace("?dl=0", "?dl=1")
                else:
                    shared_link = dbx_client.dbx.sharing_create_shared_link_with_settings(finalized_path)
                    download_url = shared_link.url.replace("?dl=0", "?dl=1")
            except Exception:
                shared_link = dbx_client.dbx.sharing_create_shared_link_with_settings(finalized_path)
                download_url = shared_link.url.replace("?dl=0", "?dl=1")

            return {
                "status": "success",
                "message": f"Fichier {filename} traité avec succès",
                "finalized_path": finalized_path,
                "download_url": download_url,
                "qr_id": str(q.id),
                "slug": q.slug
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing {filename}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))