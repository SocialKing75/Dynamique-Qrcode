from fastapi import APIRouter, Request, BackgroundTasks, Header
from fastapi.responses import PlainTextResponse
from .dropbox_client import DropboxClient
from . import models, schemas
from .utils import generate_slug
from .pdf_utils import add_qr_to_pdf
import os
import tempfile
import asyncio
import logging
import dropbox

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])
dbx_client = DropboxClient()
logger = logging.getLogger(__name__)

@router.get("/dropbox")
async def verify_dropbox(challenge: str):
    """
    Dropbox webhook verification.
    Dropbox sends a challenge and expects the same value back as plain text.
    """
    # Return the raw challenge value as plain text
    return PlainTextResponse(content=challenge)

@router.get("/debug-config")
async def debug_config():
    """Check if environment variables are set and list folder contents."""
    def get_token_info(key):
        val = os.getenv(key, "").strip()
        if not val: return "missing"
        # Prefix (10 chars to distinguish sl.u. vs 9F6- etc.) and length
        return f"set (prefix: {val[:10]}..., len: {len(val)})"

    config = {
        "DROPBOX_APP_KEY": get_token_info("DROPBOX_APP_KEY"),
        "DROPBOX_APP_SECRET": get_token_info("DROPBOX_APP_SECRET"),
        "DROPBOX_REFRESH_TOKEN": get_token_info("DROPBOX_REFRESH_TOKEN"),
        "DROPBOX_FOLDER_PATH": os.getenv("DROPBOX_FOLDER_PATH", "/Dossier test qrcode (default)"),
        "BASE_URL": os.getenv("BASE_URL", "not-set"),
        "is_client_initialized": dbx_client.is_configured(),
        "folder_listing": []
    }
    
    if dbx_client.is_configured():
        try:
            # Test a simple call
            res = dbx_client.list_folder_changes()
            config["folder_listing"] = [e.name for e in res.entries[:10]]
            config["total_found"] = len(res.entries)
        except Exception as e:
            config["error_listing"] = str(e)
            config["error_type"] = type(e).__name__
            
    return config

@router.post("/dropbox")
async def handle_dropbox_notification(
    request: Request, 
    background_tasks: BackgroundTasks,
    x_dropbox_signature: str = Header(None)
):
    """
    Handle Dropbox file change notifications.
    """
    try:
        body = await request.json()
        logger.info(f"Dropbox notification received: {body}")
        
        # Dropbox check connection first
        if not body or "list_folder" not in body:
            return {"status": "received"}

        background_tasks.add_task(process_dropbox_changes)
        return {"status": "accepted"}
    except Exception as e:
        logger.error(f"Error in webhook: {e}")
        return {"error": str(e)}, 500

async def process_dropbox_changes():
    if not dbx_client.is_configured():
        logger.warning("Dropbox not configured, skipping check")
        return

    try:
        folder_to_check = os.getenv("DROPBOX_FOLDER_PATH", "/Dossier test qrcode")
        logger.info(f"Checking for changes in: {folder_to_check}")
        
        results = dbx_client.list_folder_changes()
        logger.info(f"Found {len(results.entries)} entries in folder.")
        
        for entry in results.entries:
            logger.debug(f"Checking entry: {entry.name} ({entry.path_lower})")
            if isinstance(entry, dropbox.files.FileMetadata) and entry.name.lower().endswith(".pdf"):
                # Avoid re-processing if it's already in the finalized folder
                if "/finalized/" in entry.path_lower:
                    logger.info(f"Skipping already finalized file: {entry.name}")
                    continue
                
                await process_single_pdf(entry)
    except Exception as e:
        logger.error(f"Error during Dropbox change processing: {str(e)}", exc_info=True)

async def process_single_pdf(entry):
    logger.info(f"Processing PDF: {entry.name}")
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "output.pdf")
        
        try:
            # 1. Download
            dbx_client.download_file(entry.path_lower, input_path)
            
            # 2. Generate Dynamic QR Code in DB
            slug = generate_slug(7)
            while await models.QRCode.find_one(models.QRCode.slug == slug):
                slug = generate_slug(7)
            
            base_url = os.getenv("BASE_URL", "https://your-site.vercel.app")
            redirect_target = f"{base_url}/info/{slug}" # Default destination
            
            q = models.QRCode(
                slug=slug,
                title=f"Auto-generated for {entry.name}",
                content=redirect_target,
                is_dynamic=True
            )
            await q.insert()
            
            # 3. Preparation of QR Configs
            dynamic_qr_url = f"{base_url}/q/{slug}"
            fidealis_qr_url = "https://fidealis.com/verify/placeholder"
            
            qr_configs = [
                {'content': dynamic_qr_url, 'x': 450, 'y': 20, 'size': 80},
                {'content': fidealis_qr_url, 'x': 360, 'y': 20, 'size': 80}
            ]
            
            # 4. Overlay QR codes
            add_qr_to_pdf(input_path, output_path, qr_configs)
            
            # 5. Upload back to Dropbox
            final_dir = os.path.dirname(entry.path_lower)
            if final_dir == "/": final_dir = ""
            finalized_path = f"{final_dir}/finalized/{entry.name}"
            
            dbx_client.upload_file(output_path, finalized_path)
            logger.info(f"Successfully processed {entry.name} -> {finalized_path}")
            
        except Exception as e:
            logger.error(f"Failed to process {entry.name}: {e}")