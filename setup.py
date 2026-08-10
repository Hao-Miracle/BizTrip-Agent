"""Compatibility shim for editable installs with older pip versions."""

from setuptools import find_packages, setup


setup(
    name="biztrip-agent",
    version="0.1.2",
    description="Personal business trip email scanner and reimbursement report generator.",
    packages=find_packages(include=["biztrip_agent*", "common*", "phase1*", "phase2*"]),
    python_requires=">=3.8",
    install_requires=[
        "python-dotenv>=1.0.0",
        "PyPDF2>=3.0.0",
        "openpyxl>=3.1.0",
        "openai>=1.0.0",
    ],
    extras_require={
        "llm": [],
        "test": ["pytest>=8.0.0"],
    },
    entry_points={
        "console_scripts": [
            "biztrip=biztrip_agent.cli:main",
        ],
    },
)
