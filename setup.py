import os
import re
import sys
import subprocess
from shutil import rmtree

import setuptools


BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def find_version(fname):
    """Attempts to find the version number in the file names fname.
    Raises RuntimeError if not found.
    """
    version = ""
    with open(fname, "r") as fp:
        regex = re.compile(r'__version__ = [\'"]([^\'"]*)[\'"]')
        for line in fp:
            m = regex.match(line)
            if m:
                version = m.group(1)
                break
    if not version:
        raise RuntimeError("Cannot find version information")
    return version


def read(fname):
    with open(os.path.join(os.path.dirname(__file__), fname), "r") as fh:
        return fh.read()


__version__ = find_version("universal_analytics/__init__.py")


class ReleaseCommand(setuptools.Command):
    """Support setup.py release and upload on PyPi."""

    description = "Build and publish the package."

    user_options = []

    @staticmethod
    def status(s):
        """Prints things in bold."""
        print("\033[1m{0}\033[0m".format(s))

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def _run(self, s, command):
        try:
            self.status(s + "\n" + " ".join(command))
            subprocess.check_call(command)
        except subprocess.CalledProcessError as error:
            sys.exit(error.returncode)

    def run(self):
        try:
            self.status("Removing previous builds…")
            rmtree(os.path.join(BASE_DIR, "dist"))
        except OSError:
            pass

        self._run(
            "Building Source and Wheel (universal) distribution…",
            [sys.executable, "setup.py", "sdist", "bdist_wheel", "--universal"],
        )

        self._run(
            "Installing Twine dependency…",
            [sys.executable, "-m", "pip", "install", "twine"],
        )

        self._run(
            "Uploading the package to PyPI via Twine…",
            [sys.executable, "-m", "twine", "upload", "dist/*"],
        )

        self._run("Creating git tags…", ["git", "tag", f"v{__version__}"])
        self._run("Pushing git tags…", ["git", "push", "--tags"])


setuptools.setup(
    name="universal-analytics-python3",
    version=__version__,
    author="Dmitri Vasilishin",
    author_email="vasilishin.d.o@gmail.com",
    description="Universal analytics python library",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    url="https://github.com/dmvass/universal-analytics-python3",
    packages=setuptools.find_packages(exclude=("test*",)),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    keywords=["python", "analytics", "google-analytics"],
    install_requires=["httpx>=0.10.0"],
    setup_requires=["pytest-runner", "flake8"],
    tests_require=["coverage", "pytest", "pytest-asyncio", "asynctest"],
    cmdclass={"release": ReleaseCommand}
)
