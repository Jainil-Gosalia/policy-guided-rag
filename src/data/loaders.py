"""
Data loading utilities for Policy-Guided RAG
"""
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from ..config.paths import PathManager


class DataLoader:
    """Centralized data loading using config"""

    def __init__(self, path_manager: Optional[PathManager] = None):
        self.path_manager = path_manager or PathManager()

    def load_dataset(self, dataset_name: str = 'manual') -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """Load a dataset by name

        Args:
            dataset_name: 'manual' or 'synthetic'

        Returns:
            Tuple of (cards, guidance, queries)
        """
        cards_path = self.path_manager.get_cards_path(dataset_name)
        guidance_path = self.path_manager.get_guidance_path(dataset_name)
        queries_path = self.path_manager.get_queries_path(dataset_name)

        with open(cards_path, 'r') as f:
            cards = json.load(f)

        with open(guidance_path, 'r') as f:
            guidance = json.load(f)

        with open(queries_path, 'r') as f:
            queries = json.load(f)

        return cards, guidance, queries

    def load_cards(self, dataset: str = 'manual') -> List[Dict]:
        """Load cards data"""
        path = self.path_manager.get_cards_path(dataset)
        with open(path, 'r') as f:
            return json.load(f)

    def load_guidance(self, dataset: str = 'manual') -> List[Dict]:
        """Load guidance data"""
        path = self.path_manager.get_guidance_path(dataset)
        with open(path, 'r') as f:
            return json.load(f)

    def load_queries(self, dataset: str = 'manual') -> List[Dict]:
        """Load queries data"""
        path = self.path_manager.get_queries_path(dataset)
        with open(path, 'r') as f:
            return json.load(f)

    def load_processed_chunks(self, dataset_name: str = 'manual') -> Tuple[List[Dict], List[Dict]]:
        """Load processed chunk data

        Args:
            dataset_name: Dataset name (e.g., 'manual')

        Returns:
            Tuple of (context_chunks, guidance_chunks)
        """
        processed_dir = self.path_manager.project_root / "data" / "processed"

        with open(processed_dir / f"{dataset_name}_context_chunks.json", 'r') as f:
            context_chunks = json.load(f)

        with open(processed_dir / f"{dataset_name}_guidance_chunks.json", 'r') as f:
            guidance_chunks = json.load(f)

        return context_chunks, guidance_chunks

    def get_dataset_info(self, dataset_name: str) -> Dict[str, Any]:
        """Get metadata about a dataset"""
        return self.path_manager.get_dataset_info(dataset_name)

    def list_datasets(self) -> List[str]:
        """List available datasets"""
        return self.path_manager.list_available_datasets()