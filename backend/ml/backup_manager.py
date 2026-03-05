"""
Model Backup Manager for PulseTrakAI™

Manages backup copies of ML models:
- Backup before model replacement
- Keep 30-day rolling history
- Enable restore from any backup
- Automatic cleanup of old backups

© PUBLIUS33™ — PulseTrakAI™ — All Rights Reserved.
"""
import os
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List

logger = logging.getLogger(__name__)


class BackupManager:
    """Manages backup copies of ML models."""
    
    def __init__(self, 
                 backup_dir: str = "backups",
                 model_dir: str = "models",
                 retention_days: int = 30):
        """
        Initialize backup manager.
        
        Args:
            backup_dir: Directory to store model backups
            model_dir: Source directory for models to backup
            retention_days: Number of days to retain backups (default 30)
        """
        self.backup_dir = Path(backup_dir)
        self.model_dir = Path(model_dir)
        self.retention_days = retention_days
        
        self.backup_dir.mkdir(exist_ok=True)
        self.backup_manifest = self.backup_dir / "backup_manifest.json"
        self._load_manifest()
    
    def _load_manifest(self):
        """Load backup manifest from file."""
        if self.backup_manifest.exists():
            with open(self.backup_manifest, 'r') as f:
                self.manifest = json.load(f)
        else:
            self.manifest = {"backups": []}
    
    def _save_manifest(self):
        """Save backup manifest to file."""
        with open(self.backup_manifest, 'w') as f:
            json.dump(self.manifest, f, indent=2)
    
    def create_backup(self, model_path: str, reason: str = "pre_deployment"):
        """
        Create a backup of the current model before deployment.
        
        Args:
            model_path: Path to the model file to backup
            reason: Reason for backup (pre_deployment, recovery, etc.)
        
        Returns:
            Backup info dictionary with timestamp and path
        """
        if not os.path.exists(model_path):
            logger.error(f"Model file not found: {model_path}")
            return None
        
        # Create backup filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_name = f"model_backup_{timestamp}.pkl"
        backup_path = self.backup_dir / backup_name
        
        try:
            # Copy model file to backup
            shutil.copy2(model_path, backup_path)
            
            backup_info = {
                "id": timestamp,
                "filename": backup_name,
                "path": str(backup_path),
                "original_path": model_path,
                "created_at": datetime.utcnow().isoformat(),
                "reason": reason,
                "size_bytes": os.path.getsize(backup_path)
            }
            
            self.manifest["backups"].append(backup_info)
            self._save_manifest()
            
            logger.info(f"Backup created: {backup_name} ({backup_info['size_bytes']} bytes)")
            return backup_info
        
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None
    
    def restore_backup(self, backup_id: str, restore_path: str) -> bool:
        """
        Restore a model from backup.
        
        Args:
            backup_id: Timestamp ID of backup to restore
            restore_path: Path where to restore the model
        
        Returns:
            True if restore successful, False otherwise
        """
        backup = self._find_backup(backup_id)
        if not backup:
            logger.error(f"Backup {backup_id} not found")
            return False
        
        try:
            shutil.copy2(backup["path"], restore_path)
            logger.info(f"Restored backup {backup_id} to {restore_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False
    
    def _find_backup(self, backup_id: str) -> Optional[dict]:
        """Find backup by ID."""
        for backup in self.manifest["backups"]:
            if backup["id"] == backup_id:
                return backup
        return None
    
    def list_backups(self, limit: int = 10) -> List[dict]:
        """List recent backups."""
        return sorted(
            self.manifest["backups"],
            key=lambda x: x["created_at"],
            reverse=True
        )[:limit]
    
    def cleanup_old_backups(self) -> List[str]:
        """
        Remove backups older than retention_days.
        
        Returns:
            List of deleted backup IDs
        """
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
        deleted = []
        
        remaining = []
        for backup in self.manifest["backups"]:
            backup_date = datetime.fromisoformat(backup["created_at"])
            
            if backup_date < cutoff_date:
                # Delete the file
                try:
                    if os.path.exists(backup["path"]):
                        os.remove(backup["path"])
                    deleted.append(backup["id"])
                    logger.info(f"Deleted old backup: {backup['filename']}")
                except Exception as e:
                    logger.error(f"Failed to delete backup file: {e}")
            else:
                remaining.append(backup)
        
        self.manifest["backups"] = remaining
        self._save_manifest()
        
        logger.info(f"Cleanup completed: {len(deleted)} backups deleted")
        return deleted
    
    def get_backup_info(self, backup_id: str) -> Optional[dict]:
        """Get detailed info for a specific backup."""
        return self._find_backup(backup_id)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    manager = BackupManager()
    
    # Example usage
    print("Recent backups:")
    for backup in manager.list_backups():
        print(f"  - {backup['filename']}: {backup['reason']}")
