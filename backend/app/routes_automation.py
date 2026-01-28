from fastapi import APIRouter, Request, HTTPException, Body, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from .dropbox_client import DropboxClient
from . import models, schemas
from .utils import generate_slug
from .pdf_utils import add_qr_to_pdf
import os
import tempfile
import logging
import dropbox
import hashlib
import hmac

router = APIRouter(prefix="/api/automation", tags=["automation"])
dbx_client = DropboxClient()
logger = logging.getLogger(__name__)

VERSION = "2026-01-28-1830"

# =============================================================================
# DROPBOX WEBHOOK - Détection en temps réel
# =============================================================================

@router.get("/dropbox-webhook")
async def dropbox_webhook_verify(challenge: str = Query(...)):
    """
    Vérification du webhook Dropbox.
    Dropbox envoie une requête GET avec un paramètre 'challenge' lors de la configuration.
    On doit retourner ce challenge en texte brut.
    """
    logger.info(f"Dropbox webhook verification received, challenge: {challenge[:20]}...")
    return PlainTextResponse(content=challenge)


@router.post("/dropbox-webhook")
async def dropbox_webhook_notification(request: Request):
    """
    Reçoit les notifications Dropbox en temps réel.
    Dropbox notifie ce endpoint dès qu'un fichier est ajouté/modifié.
    """
    # Vérifier la signature (optionnel mais recommandé)
    signature = request.headers.get("X-Dropbox-Signature", "")
    body = await request.body()

    app_secret = os.getenv("DROPBOX_APP_SECRET", "")
    if app_secret and signature:
        expected_sig = hmac.new(
            app_secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            logger.warning("Invalid Dropbox webhook signature")
            raise HTTPException(status_code=403, detail="Invalid signature")

    # Parser le body JSON
    try:
        data = await request.json()
    except Exception:
        data = {}

    logger.info(f"Dropbox webhook notification received: {data}")

    # Traiter les changements immédiatement (Vercel serverless ne supporte pas bien les background tasks)
    base_url = (os.getenv("BASE_URL") or str(request.base_url)).rstrip('/')

    result = await process_dropbox_changes(base_url)

    return JSONResponse(content={
        "status": "processed",
        "result": result
    })


async def process_dropbox_changes(base_url: str) -> dict:
    """
    Traite les changements Dropbox.
    Appelé après réception d'une notification webhook.
    Retourne un résumé du traitement.
    """
    logger.info("Processing Dropbox changes from webhook notification...")

    if not dbx_client.is_configured():
        logger.error("Dropbox not configured")
        return {"error": "Dropbox not configured"}

    result = {"processed": [], "skipped": [], "errors": []}

    try:
        # Lister tous les fichiers du dossier
        res = dbx_client.list_folder_changes()
        all_entries = list(res.entries)

        while res.has_more:
            res = dbx_client.dbx.files_list_folder_continue(res.cursor)
            all_entries.extend(res.entries)

        # Filtrer uniquement les PDF (pas dans /finalized/)
        pdf_files = [
            e for e in all_entries
            if isinstance(e, dropbox.files.FileMetadata)
            and e.name.lower().endswith('.pdf')
            and '/finalized/' not in e.path_lower
        ]

        for entry in pdf_files:
            # Vérifier si déjà traité
            existing = await models.ProcessedFile.find_one(
                models.ProcessedFile.dropbox_path == entry.path_lower
            )

            if existing and existing.content_hash == entry.content_hash:
                result["skipped"].append(entry.name)
                continue  # Déjà traité, même contenu

            # Traiter le nouveau fichier
            try:
                processed = await _process_single_file(entry, base_url)
                result["processed"].append(processed)
                logger.info(f"✅ Processed new file: {entry.name}")
            except Exception as e:
                logger.error(f"❌ Error processing {entry.name}: {e}")
                result["errors"].append({"filename": entry.name, "error": str(e)})
                # Enregistrer ou mettre à jour l'erreur
                existing_error = await models.ProcessedFile.find_one(
                    models.ProcessedFile.dropbox_path == entry.path_lower
                )
                if existing_error:
                    existing_error.status = "error"
                    existing_error.error_message = str(e)
                    existing_error.content_hash = entry.content_hash
                    await existing_error.save()
                else:
                    await models.ProcessedFile(
                        dropbox_path=entry.path_lower,
                        filename=entry.name,
                        content_hash=entry.content_hash,
                        status="error",
                        error_message=str(e)
                    ).insert()

        logger.info(f"Webhook processing complete: {len(result['processed'])} files processed")
        return result

    except Exception as e:
        logger.error(f"Error in webhook processing: {e}")
        return {"error": str(e)}


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
async def manual_process_pdf(request: Request, data: dict = Body(...)):
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

            # Use request URL to build base_url automatically
            base_url = str(request.base_url).rstrip('/')
            # Default content - user should update this in admin
            default_content = "https://example.com"

            q = models.QRCode(
                slug=slug,
                title=f"PDF: {target_entry.name}",
                content=default_content,
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
                # Attempt to get existing link or create new one
                links = dbx_client.dbx.sharing_list_shared_links(path=finalized_path, direct_only=True).links
                if links:
                    download_url = links[0].url.replace("?dl=0", "?dl=1")
                else:
                    shared_link = dbx_client.dbx.sharing_create_shared_link_with_settings(finalized_path)
                    download_url = shared_link.url.replace("?dl=0", "?dl=1")
            except Exception as e:
                # Clear error for scope issues
                if "sharing.write" in str(e) or "not_permitted" in str(e).lower():
                    logger.warning(f"Permission 'sharing.write' manquante: {e}")
                    # On ne peut pas donner de lien de téléchargement direct
                    download_url = None
                else:
                    download_url = None
                    logger.error(f"Error creating link: {e}")

            return {
                "status": "success",
                "message": f"Fichier {filename} traité et sauvegardé sur Dropbox",
                "finalized_path": finalized_path,
                "download_url": download_url,
                "scope_error": download_url is None,
                "qr_id": str(q.id),
                "slug": q.slug,
                "admin_url": f"{base_url}/admin",
                "qr_redirect_url": f"{base_url}/q/{q.slug}",
                "note": "Allez dans l'admin pour définir le lien de destination du QR code"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing {filename}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/watch")
async def watch_folder(request: Request):
    """
    Détecte et traite automatiquement les nouveaux fichiers PDF dans le dossier Dropbox.
    Appelez cet endpoint périodiquement (cron) ou via webhook.
    """
    if not dbx_client.is_configured():
        raise HTTPException(status_code=500, detail="Dropbox not configured")

    # Priorité à BASE_URL (important pour le cron Vercel)
    base_url = (os.getenv("BASE_URL") or str(request.base_url)).rstrip('/')
    results = {"processed": [], "skipped": [], "errors": []}

    try:
        # Lister tous les fichiers du dossier
        res = dbx_client.list_folder_changes()
        all_entries = list(res.entries)

        # Pagination si nécessaire
        while res.has_more:
            res = dbx_client.dbx.files_list_folder_continue(res.cursor)
            all_entries.extend(res.entries)

        # Filtrer uniquement les PDF (pas dans /finalized/)
        pdf_files = [
            e for e in all_entries
            if isinstance(e, dropbox.files.FileMetadata)
            and e.name.lower().endswith('.pdf')
            and '/finalized/' not in e.path_lower
        ]

        for entry in pdf_files:
            # Vérifier si déjà traité
            existing = await models.ProcessedFile.find_one(
                models.ProcessedFile.dropbox_path == entry.path_lower
            )

            if existing:
                # Vérifier si le fichier a changé (content_hash différent)
                if existing.content_hash == entry.content_hash:
                    results["skipped"].append({
                        "filename": entry.name,
                        "reason": "already_processed"
                    })
                    continue

            # Traiter le nouveau fichier
            try:
                processed = await _process_single_file(entry, base_url)
                results["processed"].append(processed)
            except Exception as e:
                logger.error(f"Error processing {entry.name}: {e}")
                results["errors"].append({
                    "filename": entry.name,
                    "error": str(e)
                })
                # Enregistrer l'erreur
                await models.ProcessedFile(
                    dropbox_path=entry.path_lower,
                    filename=entry.name,
                    content_hash=entry.content_hash,
                    status="error",
                    error_message=str(e)
                ).insert()

        return {
            "status": "success",
            "summary": {
                "total_found": len(pdf_files),
                "processed": len(results["processed"]),
                "skipped": len(results["skipped"]),
                "errors": len(results["errors"])
            },
            "details": results
        }

    except Exception as e:
        logger.error(f"Watch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _process_single_file(entry, base_url: str) -> dict:
    """Traite un seul fichier PDF et retourne les infos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pdf")
        output_path = os.path.join(tmpdir, "output.pdf")

        # Download
        dbx_client.download_file(entry.path_lower, input_path)

        # Generate slug
        slug = generate_slug(7)
        while await models.QRCode.find_one(models.QRCode.slug == slug):
            slug = generate_slug(7)

        # Create QR code in DB
        q = models.QRCode(
            slug=slug,
            title=f"PDF: {entry.name}",
            content="https://example.com",  # Default, to be updated in admin
            is_dynamic=True
        )
        await q.insert()

        # Add QR to PDF
        dynamic_qr_url = f"{base_url}/q/{slug}"
        qr_configs = [{'content': dynamic_qr_url, 'x': 450, 'y': 20, 'size': 80}]
        add_qr_to_pdf(input_path, output_path, qr_configs)

        # Upload to finalized folder
        final_dir = os.path.dirname(entry.path_lower)
        if final_dir == "/" or not final_dir:
            final_dir = ""
        finalized_path = f"{final_dir}/finalized/{entry.name}"
        dbx_client.upload_file(output_path, finalized_path)

        # Record as processed (upsert to handle re-processing)
        existing = await models.ProcessedFile.find_one(
            models.ProcessedFile.dropbox_path == entry.path_lower
        )
        if existing:
            existing.content_hash = entry.content_hash
            existing.qrcode_id = q.id
            existing.status = "success"
            existing.error_message = None
            await existing.save()
        else:
            await models.ProcessedFile(
                dropbox_path=entry.path_lower,
                filename=entry.name,
                content_hash=entry.content_hash,
                qrcode_id=q.id,
                status="success"
            ).insert()

        return {
            "filename": entry.name,
            "slug": slug,
            "qr_url": dynamic_qr_url,
            "finalized_path": finalized_path
        }