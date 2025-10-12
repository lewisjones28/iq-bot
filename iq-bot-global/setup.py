from setuptools import setup, find_packages

setup(
    name="iq-bot-global",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,  # Add this to include MANIFEST.in files
    install_requires=[
        "pyyaml>=6.0.1",
        "redis>=6.0.0",
        "python-dotenv>=1.0.0",
    ],
    python_requires=">=3.9",
)
