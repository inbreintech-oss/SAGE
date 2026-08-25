"""Setuptools packaging metadata for the SAG-E (sage) Python package."""

from pathlib import Path

from setuptools import find_packages, setup

ROOT = Path(__file__).resolve().parent
README = (ROOT / "README.md").read_text(encoding="utf-8") if (ROOT / "README.md").exists() else ""

setup(
    name="sage",
    version="0.1.0",
    description="SAG-E — Schema-Augmented Generation & Execution framework",
    long_description=README,
    long_description_content_type="text/markdown",
    author="Inbrein",
    author_email="inbreintech@inbrein.com",
    url="https://github.com/inbreintech-oss/SAGE.git",
    license="MIT",
    license_files=("LICENSE",),
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    python_requires=">=3.11.7",
    install_requires=[
        "fastmcp",
        "pydantic>=2.0",
        "pandas",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    project_urls={
        "Source": "https://github.com/inbreintech-oss/SAGE",
        "Bug Tracker": "https://github.com/inbreintech-oss/SAGE/issues",
    },
)
