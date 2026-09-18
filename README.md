# Orchestrate

![Orchestrate banner](images/orchestrate-git-banner.png)

<p align="center">
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python 3.10+"></a>
  <a href="https://pypi.org/project/ultralytics/"><img src="https://img.shields.io/badge/Ultralytics-8.3.161%2B-red.svg" alt="Ultralytics 8.3.161+"></a>
</p>

Orchestrate is a research pipeline for automated CT-series labeling. It combines topogram (scout/localizer) analysis, DICOM metadata, anatomical detection, and series-level image classification to convert a CT study into structured metadata.

> **Model availability:** This repository contains the pipeline and inference code, but not the trained model checkpoints. The checkpoints cannot currently be published because of privacy and data-governance restrictions. Authorized users must obtain the weights separately and provide them locally.

## What the pipeline does

At a high level, Orchestrate:

1. Reads a study and groups its DICOM instances into series.
2. Identifies and preprocesses the topogram.
3. Classifies topogram orientation and broad anatomical coverage.
4. Detects anatomical regions, landmarks, foreign metal, and lateral-brain cases on the topogram.
5. Uses the topogram detections and DICOM geometry to select relevant axial CT series.
6. Classifies reconstruction kernel and contrast enhancement for applicable series.
7. Records predictions, derived metadata, processing errors, and selected image views in local SQLite databases.

The code is intended for research and data-processing workflows. It is not a medical device and must not be used for clinical decision-making without appropriate validation, governance, and regulatory oversight.

## Requirements

- Python 3.10 or newer.
- A CUDA-capable PyTorch/CuPy environment for the current inference path.
- Authorized model checkpoints, stored locally as described below.
- DICOM studies with sufficient metadata to identify series, modality, orientation, and slice positions.

The pinned Python dependencies are defined in [`pyproject.toml`](pyproject.toml).

## Installation

```bash
git clone https://github.com/UMEssen/Orchestrate.git
cd Orchestrate
poetry install
```

If you use a different environment manager, install the dependencies from `pyproject.toml` and make sure the resulting environment provides compatible CUDA, PyTorch, and CuPy versions.

## Model checkpoints

Create the local checkpoint directory and copy the authorized weights into it:

```bash
mkdir -p checkpoints
# Copy the nine authorized .pt files into checkpoints/
ls checkpoints
```

The directory should contain:

```text
checkpoints/
├── brain_contrast.pt
├── contrast.pt
├── fremdmetall.pt
├── kernel_new.pt
├── lateral_rapid_brain.pt
├── rapid_bodypart.pt
├── rapid_organ.pt
├── rapid_region.pt
└── viewposition.pt
```

The following table reflects the checkpoint names and call sites in the current implementation. The files themselves are deliberately excluded from this repository.

| Checkpoint | Prepared input | Model task | Prediction | Used for |
| --- | --- | --- | --- | --- |
| `viewposition.pt` | 640 × 640 topogram | Classification | `Lateral` or `Non-Lateral` | Topogram orientation. |
| `rapid_bodypart.pt` | 640 × 640 topogram | Classification | `head`, `brain_neck`, `torso`, `hands`, or `legs` | Broad anatomical coverage and routing. |
| `rapid_region.pt` | 640 × 640 topogram | Object detection | Region bounding boxes/classes | `head`, `thoracic_region`, `abdominal_region`, and `pericardium` coverage. |
| `rapid_organ.pt` | 640 × 640 topogram | Object detection | Landmark bounding boxes/classes | Lung, heart, spine, liver, kidneys, spleen, stomach, colon, pancreas, brain, and hip landmarks. |
| `lateral_rapid_brain.pt` | 640 × 640 lateral topogram | Object detection | Brain detections | Lateral-brain routing. |
| `fremdmetall.pt` | Normalized topogram image | Object detection | Foreign-metal detections | Foreign-metal screening in the scan range. |
| `kernel_new.pt` | Center-slice CT image | Classification | Soft or hard kernel | Reconstruction-kernel classification for axial body CT. |
| `contrast.pt` | Four-slice CT gallery with soft-tissue windowing | Classification | Native or contrast-enhanced | Contrast classification for axial body CT. |
| `brain_contrast.pt` | Four-slice padded CT gallery | Classification | Native or contrast-enhanced | Contrast classification for lateral-brain/head CT. |

The topogram-based anatomical components are related to the [UMEssen/RAPID repository](https://github.com/UMEssen/RAPID), which contains the published RAPID body-region work.

## Input data

The current API accepts DICOM studies only. A single study should contain its DICOM series below one study directory. For batch processing, place multiple study directories below one parent directory.

Example layout:

```text
single-study/
├── series-001/
│   ├── image-0001.dcm
│   └── image-0002.dcm
└── series-002/
    ├── image-0001.dcm
    └── image-0002.dcm

all-studies/
├── study-001/
│   ├── series-001/
│   └── series-002/
└── study-002/
    ├── series-001/
    └── series-002/
```

The input path must be readable by the process running Orchestrate. Do not commit DICOM files, patient metadata, screenshots containing patient information, or generated databases.

## Run the pipeline

### 1. Start the API

The API is served with Uvicorn. If physical GPU 3 should be used, expose it as the process-local `cuda:0` device:

```bash
CUDA_VISIBLE_DEVICES=3 ORCHESTRATE_DEVICE=cuda:0 \
  uvicorn main:app --reload --port 8001
```

If the intended GPU is already the first visible GPU:

```bash
ORCHESTRATE_DEVICE=cuda:0 uvicorn main:app --reload --port 8001
```

Open the interactive API documentation at <http://127.0.0.1:8001/docs>.

### 2. Process one study

```bash
curl -X POST 'http://127.0.0.1:8001/orchestrate' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "path": "/path/to/single-study",
    "file_type": "dcm"
  }'
```

### 3. Process a batch of studies

```bash
curl -X POST 'http://127.0.0.1:8001/orchestrate_all' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "path": "/path/to/all-studies",
    "file_type": "dcm"
  }'
```

The API validates the input directory and checkpoint manifest before starting inference. Missing checkpoints result in HTTP 503; unsupported input types result in HTTP 400; unexpected processing failures result in HTTP 500 and are logged.

A successful single-study request normally returns:

```json
{"study_path":"study-001","result":"complete"}
```

Studies that cannot be routed—for example, because the topogram is invalid or the anatomical coverage is unsupported—are recorded in the error tables and return a descriptive result.

## Runtime configuration

The default paths assume that the API is started from the repository, but all important runtime locations can be overridden with environment variables.

| Variable | Purpose | Default |
| --- | --- | --- |
| `ORCHESTRATE_DEVICE` | PyTorch/Ultralytics inference device | `cuda:0` when CUDA is available |
| `ORCHESTRATE_CHECKPOINT_DIR` | Directory containing the `.pt` files | `<repository>/checkpoints` |
| `ORCHESTRATE_OUTPUT_DB` | Database containing pipeline results | `<repository>/db/orchestrait.db` |
| `ORCHESTRATE_METADATA_DB` | Temporary DICOM-discovery database | `<repository>/db/metadata.db` |
| `ORCHESTRATE_LOG_DIR` | API log directory | `<repository>/logs` |

Example:

```bash
ORCHESTRATE_CHECKPOINT_DIR=/opt/orchestrate/checkpoints \
ORCHESTRATE_OUTPUT_DB=/opt/orchestrate/results/orchestrait.db \
ORCHESTRATE_DEVICE=cuda:0 \
uvicorn main:app --port 8001
```

## Outputs and databases

Orchestrate maintains two local SQLite databases:

- `metadata.db` stores temporary DICOM series-discovery information.
- `orchestrait.db` stores predictions, anatomical regions, landmarks, de-identification records, and processing errors.

The result database contains study and series identifiers, topogram predictions, detected regions and landmarks, reconstruction kernel, contrast status, foreign-metal detections, plane information, and processing errors. The databases and API logs are generated runtime artifacts and are ignored by Git.

## Streamlit viewer

The optional viewer displays selected study and series information. Set its data locations before launching it:

```bash
export ORCHESTRATE_VIEWER_CSV=/path/to/target-cases.csv
export ORCHESTRATE_VIEWER_STUDIES=/path/to/studies
streamlit run dashboard/app_advance.py
```

The viewer reads the result database from `ORCHESTRATE_OUTPUT_DB`, or from `<repository>/db/orchestrait.db` by default. Use it only in a controlled environment when working with patient data.

## Development checks

The repository includes checks that do not require private checkpoints or patient data:

```bash
python3 -m compileall -q main.py models utils db dashboard tests
python3 -m unittest discover -s tests -v
```

These checks cover Python compilation and the shared checkpoint/runtime configuration. End-to-end inference testing requires authorized checkpoints, a compatible CUDA environment, and representative DICOM data.

## Limitations and responsible use

- The trained checkpoints are not distributed because they cannot currently be released for privacy reasons.
- Reproducibility requires the corresponding authorized checkpoints, compatible CUDA/PyTorch dependencies, and suitable validation data.
- The current implementation expects DICOM metadata and series organization compatible with its preprocessing code.
- Unsupported modalities, missing DICOM tags, non-axial series, and failed detections may be skipped or recorded as processing errors.
- Foreign-metal class names remain generic in this public release because the final restricted class mapping is not included.
- Model predictions are research outputs and require independent validation before use in downstream studies.
- Institutional data-protection, ethics, and information-security requirements remain the responsibility of the deploying team.

## Citation

### Orchestrate

> **Publication record pending:** Add the final Orchestrate manuscript citation and DOI here once available.

### RAPID

The anatomical topogram-labeling components are related to the RAPID work:

- Repository: [UMEssen/RAPID](https://github.com/UMEssen/RAPID)
- Publication: [Topogram-based anatomical labelling of CT series](https://link.springer.com/article/10.1007/s00330-026-12830-y)

```text
Wen, Y., Kohnke, J., Parmar, V., Bojahr, C., Arzideh, K., Schmidt, C. S., ... & Hosch, R. (2026). Topogram-based anatomical labelling of CT series: anatomy-aware CT data processing using deep learning. European Radiology, 1-11.
```

## License

This project is released under the [MIT License](LICENSE). The license applies to the code in this repository; it does not grant access to restricted training data or unpublished model checkpoints.
