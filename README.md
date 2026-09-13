# Orchestrate
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Supported Poetry version](https://img.shields.io/badge/poetry_1.8.3+-black)](https://pypi.org/project/ultralytics/)
[![Supported Python version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/release/python-31011/)
[![Supported Yolo version](https://img.shields.io/badge/Ultralytics_8.3.161+-red)](https://pypi.org/project/ultralytics/)
![alt text](images/orchestrate-git-banner.png "Orchestrate")
---
## ⚠️ Under Active Development

This project is currently undergoing fixes and improvements. Please do not use or deploy this code until this notice is removed.

---
## Installation

```bash
git clone https://github.com/UMEssen/Orchestrate.git
cd Orchestrate
poetry install
```

---

## Models
| Model | Output | Notes |
| --- | --- | --- |
| `View Position` | `Lateral`, `Non-Lateral` | Determines the anatomical plane of the topogram |
| `RAPID Classification` | `Head`,  `Upper Extremities`, `Lower Extremities`,`Torso`| Classifies the anatomical coverage of the topogram |
| `RAPID Body Regions` | `Head`,  `Abdominal Region`, `Thoracic Region`,`Pericardium`| Detects and localizes body regions of the topogram |
| `RAPID Landmarks` | `Lung`,  `Heart`, `Spine`,`Liver`,`Kidneys`,`Spleen`,`Stomach`,`Colon`,`Pancreas`,`Brain`,`Hip`| Detects and localizes landmarks of the topogram |
| `Reconstruction Kernel` | `Soft Kernel`,  `Hard Kernel`| Differentiates soft and hard kernel of the body CT series |
| `Body Contrast Enhancement` | `Native`,  `Contrast Enhancement (CE)`| Differentiates whether IV contrast enhancement is present in the body CT series |
| `Brain Contrast Enhancement` | `Native`,  `Contrast Enhancement (CE)`| Differentiates whether IV contrast enhancement is present in the head CT series |


## Performance
```bash
cd dashboard
streamlit run app_advance.py
```
![alt text](images/orchestrate-viewer.png "Orchestrate Viewer")

## Citation

please cite the following papers:

[Orchestrate](xxxx):


[RAPID](https://link.springer.com/article/10.1007/s00330-026-12830-y):

```text
Wen, Y., Kohnke, J., Parmar, V., Bojahr, C., Arzideh, K., Schmidt, C. S., ... & Hosch, R. (2026). Topogram-based anatomical labelling of CT series: anatomy-aware CT data processing using deep learning. European Radiology, 1-11.
```