from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="gemini-cli",
    version="0.2.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Convert natural language to shell commands using Gemini API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/gemini-cli",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Environment :: Console",
        "Topic :: Utilities",
    ],
    python_requires=">=3.7",
    install_requires=[
        "google-generativeai>=0.3.0",
        "rich>=12.0.0",
        "toml>=0.10.2",
    ],
    entry_points={
        "console_scripts": [
            "gemini-cli=cli.main:main",
        ],
    },
) 