# Third-party notices

This repository contains launch scripts, manifests, and documentation. It does **not** redistribute model weights, drafter weights, or container layers.

## Target checkpoint

`neko-legends/GLM-5.3-Flash-Uncensored-EXL3@1fac3dbe6269a399ce5378261cdf250fde706180` is a mixed-license, gated artifact. Its card states:

- the `zai-org` → uncensored FP8 model-weight chain is MIT;
- inherited ShapleyMCG-calibrated scale tensors and related calibration/encoding portions are under ShapleyMCG License 1.0;
- access to the uncensored checkpoint is gated and requires acceptance of its terms.

The complete ShapleyMCG text is included at `THIRD_PARTY_LICENSES/ShapleyMCG-LICENSE-1.0.txt`. Its SHA-256 is `9a354667162e40201fa556e29ae7a327cdb112eacaa8ef100106e6063635e28a`.

The original Z.ai GLM-5.3 Flash BF16 MIT text is included for lineage attribution at `THIRD_PARTY_LICENSES/ZAI-GLM-5.3-Flash-BF16-MIT.txt`; it does not override licenses attached to derivative checkpoint layers.

## DFlash2 drafter

`incoai/GLM-5.3-Flash-DFlash2@7d74cdd881ed7e32c31175984a67823127b66cfe` is licensed under Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International.

- Non-commercial use only unless separately licensed.
- Attribution is required.
- Sharing adapted material is not permitted under that license.
- Commercial licensing contact listed by its model card: `contact@inco.ai`.

The legal code is included at `THIRD_PARTY_LICENSES/CC-BY-NC-ND-4.0.txt`.

## Runtime image

The recipe pulls this external image by digest:

`verdictai/glm53-flash-exl3-k4:r19-sm120-tp2-ep2-dcp2-v84-dflash2@sha256:0f1cdcc8891f1cc3a444121eb61d366289a1cbba285f0892dcbb24bc94961692`

Its OCI labels declare `LicenseRef-ShapleyMCG-1.0`, Brandon M. Music as author, and `https://github.com/brandonmmusic-max/glm-5.3-flash-exl3-4bpw` as source. The image contains many independently licensed projects. This repository preserves its embedded provenance but has not independently reconstructed every binary layer. The recipe does not grant rights to mirror or redistribute the image.

The image also embeds this NVIDIA notice; the single OCI ShapleyMCG label does not replace it or the licenses of other bundled components:

> Various files include modifications (c) NVIDIA CORPORATION & AFFILIATES. All rights reserved.
>
> GOVERNING TERMS: The software and materials are governed by the NVIDIA Software License Agreement (found at https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-software-license-agreement/) and the Product-Specific Terms for NVIDIA AI Products (found at https://www.nvidia.com/en-us/agreements/enterprise-software/product-specific-terms-for-ai-products/).

The notice is present inside the image at `/workspace/license.txt` and `/opt/nvidia/entrypoint.d/30-container-license.txt`. The pinned NVIDIA foundation image and remaining runtime-source gaps are recorded in [PROVENANCE.md](PROVENANCE.md).

## Benchmark software and data

- EvalPlus/HumanEval+ 0.3.1 is Apache-2.0 licensed.
- OpenAI HumanEval is MIT licensed.
- Gorilla/BFCL at commit `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8` is Apache-2.0 licensed.

This repository does not redistribute their datasets or generated result rows. It contains locally authored request harnesses, a minimal BFCL model-registration/output-bound patch, reproduction instructions, and aggregate scores. Upstream licenses and dataset terms remain controlling.

## Recipe license boundary

`LICENSE` applies only to this repository's original scripts and documentation under Apache-2.0. It does not relicense any model, data, calibration artifact, drafter, container, library, driver, or third-party source.
