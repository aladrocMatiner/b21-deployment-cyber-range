from setuptools import setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="crl",
    version="0.0.8",
    author="Jonas Karlsson",
    author_email="jonas.karlsson@kau.se",
    description="Cyber Range Lite (crl) cli",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://git.cs.kau.se/csma/cyber-range/crl",
    project_urls={
        "Bug Tracker": "https://git.cs.kau.se/csma/cyber-range/crl/-/issues",
    },
    classifiers=["Programming Language :: Python :: 3"],
    install_requires=[
        # crl
        "argparse",
        "pathvalidate",
        "python-on-whales",
        "pyyaml",
        "httpx",
        "requests",
        # crld+portd
        "aiohttp",
    ],
    entry_points={
        "console_scripts": [
            "crl=crl.crl:main",
            "crld=crld.__main__:main",
            "portd=portd.portd:main",
        ]
    },
    packages=["crl", "crl.services", "crl.wordlists", "crld", "portd"],
    package_data={
        "crl.services": ["*.yml"],
        "crl.wordlists": ["*.txt"],
    },
    python_requires=">=3.11",
)
