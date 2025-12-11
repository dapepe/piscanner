from setuptools import setup, find_packages

setup(
    name="piscan",
    version="1.0.0",
    description="Raspberry Pi Canon DR-F120 Scanner Automation",
    packages=find_packages(),
    install_requires=[
        "PyYAML>=6.0",
        "Flask>=2.3.0", 
        "requests>=2.31.0",
        "Pillow>=10.0.0",
    ],
    entry_points={
        "console_scripts": [
            "piscan=piscan.cli:main",
        ],
    },
    python_requires=">=3.8",
)