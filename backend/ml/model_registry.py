"""
Model Registry for PulseTrakAI™

Manages model versions and metadata:
- Version models (model_v1.pkl, model_v2.pkl, etc.)
- Store metadata (training date, dataset size, validation accuracy)
- Keep previous 3 versions
- Enable rollback to any previous version

© PUBLIUS33™ — PulseTrakAI™ — All Rights Reserved.
"""
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class ModelRegistry:
    """Registry for managing ML model versions and metadata."""
    
    def __init__(self, registry_dir: str = "models", max_versions: int = 3):
        """Initialize model registry."""
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(exist_ok=True)
        self.max_versions = max_versions
        self.metadata_file = self.registry_dir / "model_metadata.json"
        self._load_metadata()
    
    def _load_metadata(self):
        """Load model metadata from file."""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {
                "models": [],
                "current_version": None
            }
    
    def _save_metadata(self):
        """Save model metadata to file."""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    def register_model(self, model_path: str, accuracy: float, dataset_size: int):
        """Register a new model version."""
        version_num = len(self.metadata["models"]) + 1
        model_name = f"model_v{version_num}"
        
        model_info = {
            "version": version_num,
            "name": model_name,
            "path": str(model_path),
            "training_date": datetime.utcnow().isoformat(),
            "dataset_size": dataset_size,
            "validation_accuracy": accuracy,
            "status": "active"
        }
        
        self.metadata["models"].append(model_info)
        self.metadata["current_version"] = version_num
        
        # Prune old versions, keep only last N
        if len(self.metadata["models"]) > self.max_versions:
            old_models = self.metadata["models"][:-self.max_versions]
            for old in old_models:
                self._delete_model_file(old["path"])
                logger.info(f"Deleted old model: {old['name']}")
            
            self.metadata["models"] = self.metadata["models"][-self.max_versions:]
        
        self._save_metadata()
        logger.info(f"Registered model: {model_name} with accuracy {accuracy:.4f}")
        return model_info
    
    def get_latest_model(self) -> Optional[Dict]:
        """Retrieve the latest active model metadata."""
        if not self.metadata["models"]:
            logger.warning("No models in registry")
            return None
        
        return self.metadata["models"][-1]
    
    def get_model_version(self, version: int) -> Optional[Dict]:
        """Retrieve a specific model version."""
        for model in self.metadata["models"]:
            if model["version"] == version:
                return model
        
        logger.warning(f"Model version {version} not found")
        return None
    
    def list_models(self) -> List[Dict]:
        """List all registered models."""
        return self.metadata["models"]
    
    def rollback_to_version(self, version: int) -> bool:
        """Rollback to a previous model version."""
        model = self.get_model_version(version)
        if not model:
            logger.error(f"Cannot rollback: version {version} not found")
            return False
        
        # Set as current version
        self.metadata["current_version"] = version
        self._save_metadata()
        logger.info(f"Rolled back to model version {version}")
        return True
    
    def _delete_model_file(self, path: str):
        """Delete model file from disk."""
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            logger.error(f"Failed to delete model file {path}: {e}")
    
    def export_models_list(self) -> str:
        """Export models list as JSON string."""
        return json.dumps(self.metadata, indent=2)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    registry = ModelRegistry()
    
    # Example usage
    print("Current models:")
    for model in registry.list_models():
        print(f"  - {model['name']}: accuracy={model['validation_accuracy']:.4f}")
