# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tools for the Strategic Planning Agent."""


async def create_initiative(title: str, description: str, priority: str = "medium") -> dict:
    """Create a new strategic initiative.
    
    Args:
        title: Title of the initiative.
        description: Description of the initiative goals.
        priority: Priority level (low, medium, high, critical).
        
    Returns:
        Dictionary containing the created initiative.
    """
    from app.services.initiative_service import InitiativeService
    
    try:
        service = InitiativeService()
        initiative = await service.create_initiative(title, description, priority)
        return {"success": True, "initiative": initiative}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_initiative(initiative_id: str) -> dict:
    """Retrieve an initiative by ID.
    
    Args:
        initiative_id: The unique identifier of the initiative.
        
    Returns:
        Dictionary containing the initiative details.
    """
    from app.services.initiative_service import InitiativeService
    
    try:
        service = InitiativeService()
        initiative = await service.get_initiative(initiative_id)
        return {"success": True, "initiative": initiative}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def update_initiative(initiative_id: str, status: str, progress: int = None) -> dict:
    """Update initiative status and progress.
    
    Args:
        initiative_id: The unique identifier of the initiative.
        status: The new status (draft, active, completed, on_hold).
        progress: Optional progress percentage (0-100).
        
    Returns:
        Dictionary confirming the status update.
    """
    from app.services.initiative_service import InitiativeService
    
    try:
        service = InitiativeService()
        initiative = await service.update_initiative(initiative_id, status=status, progress=progress)
        return {"success": True, "initiative": initiative}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def list_initiatives(status: str = None) -> dict:
    """List all initiatives, optionally filtered by status.
    
    Args:
        status: Optional status filter (draft, active, completed, on_hold).
        
    Returns:
        Dictionary containing list of initiatives.
    """
    from app.services.initiative_service import InitiativeService
    
    try:
        service = InitiativeService()
        initiatives = await service.list_initiatives(status=status)
        return {"success": True, "initiatives": initiatives, "count": len(initiatives)}
    except Exception as e:
        return {"success": False, "error": str(e), "initiatives": []}
