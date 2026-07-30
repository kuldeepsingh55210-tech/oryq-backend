import logging
from fastapi import APIRouter, HTTPException, Depends, status, Response
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from app.auth.middleware import get_current_user
from app.agency.workspace import create_workspace, list_user_workspaces, add_brand_to_workspace, list_workspace_brands
from app.agency.whitelabel import update_whitelabel_config, get_whitelabel_config
from app.agency.reports import generate_whitelabel_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agency", tags=["Agency Tools"])

class CreateWorkspaceRequest(BaseModel):
    name: str

class AddBrandToWorkspaceRequest(BaseModel):
    brand_id: str
    client_name: Optional[str] = None

class UpdateWhitelabelRequest(BaseModel):
    agency_name: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    report_footer: Optional[str] = None

@router.post("/workspaces", status_code=status.HTTP_201_CREATED)
async def api_create_workspace(
    payload: CreateWorkspaceRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Creates a new agency workspace for the authenticated user.
    """
    try:
        user_id = current_user["id"]
        workspace = await create_workspace(user_id, payload.name)
        return workspace
    except Exception as e:
        logger.error(f"Error creating workspace: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create workspace")

@router.get("/workspaces")
async def api_list_workspaces(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Lists all workspaces owned by the authenticated user.
    """
    try:
        user_id = current_user["id"]
        workspaces = await list_user_workspaces(user_id)
        return workspaces
    except Exception as e:
        logger.error(f"Error fetching workspaces: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list workspaces")

@router.post("/workspaces/{id}/brands")
async def api_add_brand_to_workspace(
    id: str,
    payload: AddBrandToWorkspaceRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Adds a brand (client) to the specified workspace.
    """
    try:
        wb_record = await add_brand_to_workspace(
            workspace_id=id,
            brand_id=payload.brand_id,
            client_name=payload.client_name
        )
        return wb_record
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error(f"Error adding brand to workspace {id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to add brand to workspace")

@router.get("/workspaces/{id}/brands")
async def api_list_workspace_brands(
    id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Lists all brands attached to a workspace with their client names and latest scores.
    """
    try:
        brands = await list_workspace_brands(id)
        return brands
    except Exception as e:
        logger.error(f"Error fetching workspace brands for {id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch workspace brands")

@router.get("/{workspace_id}/report/{brand_id}")
async def api_get_whitelabel_report(
    workspace_id: str,
    brand_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Generates and returns a white-labeled PDF report for the given brand using agency branding settings.
    """
    try:
        pdf_bytes = await generate_whitelabel_pdf(workspace_id=workspace_id, brand_id=brand_id)
        filename = f"Whitelabel_Report_{brand_id[:8]}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"inline; filename={filename}"}
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error(f"Error generating whitelabel PDF report: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate whitelabel PDF report")

@router.get("/{workspace_id}/whitelabel")
async def api_get_whitelabel(
    workspace_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Fetches white-label branding configuration for a workspace.
    """
    try:
        config = await get_whitelabel_config(workspace_id)
        return config
    except Exception as e:
        logger.error(f"Error fetching whitelabel config for workspace {workspace_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch whitelabel configuration")

@router.patch("/{workspace_id}/whitelabel")
async def api_update_whitelabel(
    workspace_id: str,
    payload: UpdateWhitelabelRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Updates the white-label branding configurations (agency name, colors, footer, logo) for a workspace.
    """
    try:
        updated = await update_whitelabel_config(
            workspace_id=workspace_id,
            agency_name=payload.agency_name,
            logo_url=payload.logo_url,
            primary_color=payload.primary_color,
            secondary_color=payload.secondary_color,
            report_footer=payload.report_footer
        )
        return updated
    except Exception as e:
        logger.error(f"Error updating whitelabel config for workspace {workspace_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update whitelabel configuration")

