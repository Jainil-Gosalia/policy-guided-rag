from pathlib import Path

from setuptools import find_packages, setup

long_description = (Path(__file__).parent / "README.md").read_text(encoding="utf-8")

setup(
    name="policy-guided-rag",
    version="0.1.0",
    description="Policy-Guided RAG with Asymmetric Visibility for controllable retrieval",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Jainil Gosalia",
    license="MIT",
    url="https://github.com/jainilgosalia/policy-guided-rag",
    packages=find_packages(include=["src", "src.*"]),
    install_requires=[
        "chromadb==0.4.22",
        "sentence-transformers==2.3.1",
        "torch==2.1.2",
        "transformers==4.36.2",
        "pyyaml==6.0.1",
        "numpy==1.24.3",
        "pandas==2.0.3",
        "tqdm==4.66.1",
    ],
    extras_require={
        "viz": ["matplotlib==3.7.2", "seaborn==0.12.2"],
        "dev": ["pytest==7.4.3"],
    },
    python_requires=">=3.10",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)
