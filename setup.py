from setuptools import setup, find_packages
import pathlib

VERSION = "1.0"

here = pathlib.Path(__file__).parent.resolve()

long_description = (here / "README.md").read_text(encoding="utf-8")

setup(name="fmb-ic-plus",
      version=VERSION,
      license="MIT License",
      description="A module to control FMB Oxford IC Plus ionisation chamber",
      long_description=long_description,
      long_description_content_type="text/markdown",
      url="https://gitlab.kcsni.ru/tango-deviceservers/fmb-ic-plus",
      author="Andrey Pechnikov",
      classifiers=[
          "Development Status :: 3 - Alpha",
          "Intended Audience :: Science/Research",
          "Topic :: Scientific/Engineering :: Synchrotron",
          "Programming Language :: Python :: 3",
          "License :: OSI Approved :: MIT License",
          "Programming Language :: Python :: 3 :: Only",
          "Operating System :: Linux",
      ],
      py_modules=["fmb_ic_plus"],
      package_dir={"": "fmb"},
      packages=find_packages(where="fmb"),
      python_requires=">=3.7",
      install_requires=["pyserial", "pytango>=9.0.0"],
      include_package_data=True,
      zip_safe=False,
      entry_points={
            "console_scripts": [
                "FMBICPlusBus=fmb_ic_plus:main",
            ],
        },
      )
