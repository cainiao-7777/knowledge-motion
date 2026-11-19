"""把安装包运行时所需的第三方许可原文复制进本机打包目录。"""
from importlib.metadata import distribution
from pathlib import Path
import shutil
import sys

root = Path(__file__).resolve().parents[1]
bundle = root / 'outputs' / 'release-work' / 'dist' / 'KnowledgeMotion'
target = bundle / 'THIRD_PARTY_NOTICES'
target.mkdir(parents=True, exist_ok=True)

for package in ('Pillow', 'numpy', 'opencc-python-reimplemented', 'pyinstaller'):
    dist = distribution(package)
    for entry in dist.files or ():
        normalized = str(entry).replace('\\', '/')
        if '.dist-info/licenses/' not in normalized:
            continue
        relative = normalized.split('.dist-info/licenses/', 1)[1]
        source = Path(dist.locate_file(entry))
        if source.is_file():
            destination = target / package / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

opencc_distribution = distribution('opencc-python-reimplemented')
for entry in opencc_distribution.files or ():
    normalized = str(entry).replace('\\', '/')
    if normalized.endswith(('opencc/NOTICE.txt', 'opencc_python_reimplemented-0.1.7.dist-info/LICENSE.txt')):
        source = Path(opencc_distribution.locate_file(entry))
        destination = target / 'opencc-python-reimplemented' / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

python_license = Path(sys.base_prefix) / 'LICENSE.txt'
if python_license.is_file():
    shutil.copy2(python_license, target / 'Python-LICENSE.txt')

for name in ('tcl8.6', 'tk8.6'):
    license_file = Path(sys.base_prefix) / 'tcl' / name / 'license.terms'
    if license_file.is_file():
        shutil.copy2(license_file, target / f'{name}-license.terms')

tcl_license = Path(sys.base_prefix) / 'tcl' / 'tcl8.6' / 'license.terms'
if tcl_license.is_file():
    shutil.copy2(tcl_license, target / 'tcl8.6-license.terms')

for name in ('tcl-license.terms', 'tk-license.terms'):
    shutil.copy2(Path(__file__).with_name('licenses') / name, target / name)

shutil.copy2(root / 'THIRD_PARTY_NOTICES.md', bundle / 'THIRD_PARTY_NOTICES.md')

