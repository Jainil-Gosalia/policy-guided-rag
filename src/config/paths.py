"""
Path management for Policy-Guided RAG
"""
import yaml
from pathlib import Path
from typing import Optional, Dict, Any


class PathManager:
    """Centralized path handling for datasets and results"""

    def __init__(self, datasets_config_path: Optional[Path] = None):
        if datasets_config_path is None:
            datasets_config_path = Path(__file__).parent.parent.parent / "config" / "datasets.yaml"

        with open(datasets_config_path, 'r') as f:
            self.datasets = yaml.safe_load(f)

        self.project_root = Path(__file__).parent.parent.parent

    def get_dataset_path(self, dataset_name: str, file_type: str) -> Path:
        """Get path to a dataset file

        Args:
            dataset_name: Name of dataset (e.g., 'manual', 'synthetic')
            file_type: Type of file (e.g., 'cards', 'guidance', 'queries')

        Returns:
            Full path to the file
        """
        # Try both singular and plural forms
        for key in [file_type, f"{file_type}s"]:
            relative_path = self.datasets['datasets'][dataset_name]['files'].get(key)
            if relative_path is not None:
                return self.project_root / relative_path

        raise ValueError(f"Unknown file type '{file_type}' for dataset '{dataset_name}'")

    def get_cards_path(self, dataset: str = 'manual') -> Path:
        """Get path to cards file"""
        return self.get_dataset_path(dataset, 'cards')

    def get_guidance_path(self, dataset: str = 'manual') -> Path:
        """Get path to guidance file"""
        return self.get_dataset_path(dataset, 'guidance')

    def get_queries_path(self, dataset: str = 'manual') -> Path:
        """Get path to queries file"""
        return self.get_dataset_path(dataset, 'queries')

    def get_results_dir(self) -> Path:
        """Get results directory"""
        results_dir = self.project_root / "results"
        results_dir.mkdir(exist_ok=True)
        return results_dir

    def get_experiment_dir(self, experiment_name: str, create: bool = True) -> Path:
        """Get experiment results directory

        Args:
            experiment_name: Name of the experiment
            create: Whether to create the directory if it doesn't exist

        Returns:
            Path to the experiment directory
        """
        exp_dir = self.get_results_dir() / experiment_name
        if create:
            exp_dir.mkdir(parents=True, exist_ok=True)
        return exp_dir

    def get_run_dir(self, experiment_name: str) -> Path:
        """Get a unique run directory with timestamp

        Returns:
            Path like results/manual_test/run_20260219_123456/
        """
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = self.get_experiment_dir(experiment_name) / f"run_{timestamp}"
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def get_dataset_info(self, dataset_name: str) -> Dict[str, Any]:
        """Get metadata about a dataset"""
        return self.datasets['datasets'].get(dataset_name, {})

    def list_available_datasets(self) -> list:
        """List all available dataset names"""
        return list(self.datasets['datasets'].keys())