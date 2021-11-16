#!/usr/bin/env python3

import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="gpxmerge",
    version="0.0.3",
    author="rene-d",
    author_email="rene.github@gmail.com",
    description="GPXMerge",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/rene-d/gpxmerge",
    project_urls={
        "Bug Tracker": "https://github.com/rene-d/gpxmerge/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: Public Domain",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
    install_requires=["simplekml>=1.3.5", "click>=8.0.0", "gpxpy>=1.4.2"],
    entry_points={"console_scripts": ["gpxmerge=gpxmerge.gpxmerge:main"]},
)
