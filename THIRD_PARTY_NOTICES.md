# Third-party notices

This file covers third-party code included in this repository. It does not grant any license on the VisionFlow code
itself: no license has been chosen for it yet.

## YOLOX (Megvii, Base Detection)

- Source: <https://github.com/Megvii-BaseDetection/YOLOX>, tag `0.1.1rc0`.
- License: Apache License 2.0, copyright 2021 Megvii, Base Detection. Full text: [`third_party/YOLOX/LICENSE`](third_party/YOLOX/LICENSE),
  copied verbatim from the tag `0.1.1rc0`. The YOLOX repository has no `NOTICE` file at this tag.
- Used in: `passages/detection.py`. The image pre-processing (`yolox/data/data_augment.py::preproc`) and the output
  decoding, per-class non-maximum suppression (`yolox/utils/demo_utils.py`, `nms` and `multiclass_nms`) are derived
  from YOLOX. The list of the 80 COCO class names (`COCO_CLASSES`) is copied from
  `yolox/data/datasets/coco_classes.py`; the oracle in `tests/test_detection_multiclasse.py` is a frozen copy of the
  derived decoding.
- Changes: the code was adapted and rewritten for this project (NumPy / OpenCV only, no PyTorch, selectable classes
  with the person class only by default, integration with ONNX Runtime). Apart from the class-name list, it is not a
  verbatim copy.

The YOLOX **model weights** (`yolox_s.onnx`) are not included in this repository. No separate license for the
released weights was found; their legal status is not established (see `docs/DECISIONS.md`, D-022).

Python dependencies installed from `requirements.lock` are not redistributed here; each is governed by its own license.
