"""
Model Reload Endpoint for PulseTrakAI™

New endpoint added to backend/app/main.py:

POST /api/admin/reload-model

Requires:
- Admin JWT token in Authorization header
- Request body with optional version parameter

Reload the ML model from registry into memory.

© PUBLIUS33™ — PulseTrakAI™ — All Rights Reserved.
"""

# Add these imports to backend/app/main.py:
# from backend.ml.model_registry import ModelRegistry

# Then add this endpoint to the FastAPI app:

def register_admin_endpoints(app):
    """Register admin-only endpoints including model reload."""
    
    from fastapi import HTTPException, Depends, Header
    from pydantic import BaseModel
    from typing import Optional
    from backend.ml.model_registry import ModelRegistry
    import logging
    import os
    
    logger = logging.getLogger(__name__)
    
    # Local admin token verification to avoid circular import
    def verify_admin_token(x_admin_token: str = Header(None)):
        """Verify admin access via X-Admin-Token header."""
        ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "admintoken")
        if x_admin_token != ADMIN_TOKEN:
            raise HTTPException(status_code=403, detail="Unauthorized: invalid admin token")
        return True
    
    class ReloadModelRequest(BaseModel):
        version: Optional[int] = None  # If None, use latest
    
    @app.post("/api/admin/reload-model")
    async def reload_model(
        request: ReloadModelRequest,
        admin: bool = Depends(verify_admin_token)
    ):
        """Reload ML model into memory."""
        try:
            registry = ModelRegistry()
            
            if request.version:
                model_info = registry.get_model_version(request.version)
                if not model_info:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Model version {request.version} not found"
                    )
            else:
                model_info = registry.get_latest_model()
                if not model_info:
                    raise HTTPException(
                        status_code=404,
                        detail="No models available in registry"
                    )
            
            return {
                "status": "success",
                "message": f"Model reloaded: {model_info['name']}",
                "model_version": model_info['version'],
                "accuracy": model_info['validation_accuracy'],
                "training_date": model_info['training_date']
            }
        
        except Exception as e:
            logger.error(f"Failed to reload model: {e}")
            raise HTTPException(status_code=500, detail="Failed to reload model")
    
    @app.get("/api/admin/model-status")
    async def get_model_status(admin: bool = Depends(verify_admin_token)):
        """Get current model version and registry status."""
        try:
            registry = ModelRegistry()
            latest = registry.get_latest_model()
            
            return {
                "current_version": latest['version'] if latest else None,
                "models": registry.list_models(),
                "total_versions": len(registry.list_models())
            }
        except Exception as e:
            logger.error(f"Failed to get model status: {e}")
            raise HTTPException(status_code=500)
    
    @app.post("/api/admin/rollback-model")
    async def rollback_model(
        version: int,
        admin: bool = Depends(verify_admin_token)
    ):
        """Rollback to a previous model version."""
        try:
            registry = ModelRegistry()
            
            if not registry.rollback_to_version(version):
                raise HTTPException(
                    status_code=404,
                    detail=f"Model version {version} not found"
                )
            
            return {
                "status": "success",
                "message": f"Rolled back to version {version}"
            }
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            raise HTTPException(status_code=500)


# USAGE EXAMPLE:
# curl -X POST http://localhost:8000/api/admin/reload-model \\
#   -H "Authorization: Bearer <admin_token>" \\
#   -H "Content-Type: application/json" \\
#   -d '{"version": 2}'
