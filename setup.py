from setuptools import setup, find_packages

setup(
    name="code-smells",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'click',
        'anthropic',
    ],
    entry_points={
        'console_scripts': [
            'code-smells=code_smells.cli:cli',
            ],
    },
)