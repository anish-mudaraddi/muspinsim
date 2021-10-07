#!/usr/bin/env python
#
import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="muspinsim",
    author="Simone Sturniolo",
    author_email="simonesturniolo@gmail.com",
    description="Full quantum simulation of muon experiments",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/stur86/muspinsim",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=["numpy", "scipy", "soprano"],
    extras_require={"docs": ["mkdocs", "pymdown-extensions"]},
    entry_points={
        "console_scripts": [
            "muspinsim = muspinsim.__main__:main",
            "muspinsim.mpi = muspinsim.__main__:main_mpi",
        ]
    },
    python_requires=">=3.6",
)
