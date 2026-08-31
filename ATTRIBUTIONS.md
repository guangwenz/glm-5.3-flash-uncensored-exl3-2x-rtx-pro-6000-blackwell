# Attributions

## Required ShapleyMCG attribution

> This work includes or was produced using ShapleyMcg, created by Brandon M. Music
> (https://github.com/brandonmmusic-max/shapleymcg). ShapleyMcg is licensed under the
> ShapleyMcg License v1.0, an attribution-required license that grants no rights to
> the person known as "0xSero." Use of ShapleyMcg without this attribution is unlicensed.

License text: [THIRD_PARTY_LICENSES/ShapleyMCG-LICENSE-1.0.txt](THIRD_PARTY_LICENSES/ShapleyMCG-LICENSE-1.0.txt).

## Model lineage and quantization

- **Z.ai / `zai-org`** — GLM-5.3 Flash architecture and original model lineage.
- **`orcarouter` / `dealignai` lineage** — uncensored/abliterated FP8 weights, as credited by the target checkpoint card.
- **Brandon M. Music / ShapleyMCG / TR3** — calibration artifacts, EXL3/TR3 format work, and the published R10 encoder closure used by the target checkpoint.
- **MiaAI-Lab** — base EXL3 checkpoint and serving work credited by the target checkpoint author.
- **`neko-legends` (Depths)** — uncensored-weight EXL3 re-encode, verification, benchmark material, and checkpoint publication.

Target checkpoint: https://huggingface.co/neko-legends/GLM-5.3-Flash-Uncensored-EXL3

Suggested ShapleyMCG citation:

```bibtex
@misc{music2026shapleymcg,
  author = {Music, Brandon M.},
  title  = {ShapleyMCG: An Auditable Calibration-to-Encoding Pipeline for Low-Bit Mixture-of-Experts Models},
  year   = {2026},
  url    = {https://github.com/brandonmmusic-max/shapleymcg},
  note   = {Licensed under the ShapleyMcg License v1.0}
}
```

## DFlash2

- **Inco AI** — DFlash2 draft checkpoint, implementation work, and benchmark publication.
- **Jian Chen, Yesheng Liang, and Zhijian Liu** — original DFlash paper, as cited by the DFlash2 model card.

```bibtex
@misc{inco2026dflash2,
  title  = {{DFlash 2: Keep Drafting Parallel}},
  author = {{Inco AI}},
  year   = {2026},
  month  = {August},
  url    = {https://inco.ai/blog/dflash2/}
}

@inproceedings{chen2026dflash,
  title     = {{DFlash: Block Diffusion for Flash Speculative Decoding}},
  author    = {Chen, Jian and Liang, Yesheng and Liu, Zhijian},
  booktitle = {International Conference on Machine Learning (ICML)},
  year      = {2026}
}
```

DFlash2 checkpoint: https://huggingface.co/incoai/GLM-5.3-Flash-DFlash2

> `GLM-5.3-Flash-DFlash2` by Inco AI (`incoai`), revision `7d74cdd881ed7e32c31175984a67823127b66cfe`, licensed under CC BY-NC-ND 4.0: https://creativecommons.org/licenses/by-nc-nd/4.0/. Source: https://huggingface.co/incoai/GLM-5.3-Flash-DFlash2.

## Runtime image and software stack

The pinned image declares **Brandon M. Music** as author and points to `brandonmmusic-max/glm-5.3-flash-exl3-4bpw` as source. Public commit `bd5321c1cfd4b8d352ef380e3158c64886039d03` first binds the exact runtime digest used here. The registry namespace is `verdictai`; its parent image is identified under the `klc` namespace in embedded provenance. The image's own target label names the aligned `brandonmusic` checkpoint; this recipe's uncensored target substitution is independently bound by its model manifest, not by that image label.

Projects and contributors identified by the image's own labels/provenance include:

- Local Inference Lab: B12x, its vLLM integration, LMCache integration, and NCCL work
- vLLM contributors
- ExLlamaV3 contributors and Brandon M. Music's fork
- PyTorch and TorchVision contributors
- NVIDIA CUDA, NCCL, CUTLASS/CuTe, cuDNN, TensorRT, NPP, and Nsight contributors
- FlashInfer contributors and the `voipmonitor` fork/build lineage
- DeepSeek-AI DeepGEMM contributors
- InstantTensor and `voipmonitor` contributors
- xGrammar / MLC contributors
- Hugging Face Hub and Transformers contributors
- Docker/Moby and NVIDIA Container Toolkit contributors

Exact repositories and commits are preserved in [manifests/runtime-image-provenance.json](manifests/runtime-image-provenance.json) and [PROVENANCE.md](PROVENANCE.md). These credits do not imply endorsement.

## Benchmark projects

### Performance optimization and matched-checkpoint comparison

- **Samuel Cardillo** — experiment design, local qualification, fixed-fixture tuning harness, measurements, production selection, and public documentation.
- **vLLM and Local Inference Lab runtime contributors** — scheduler, Prometheus metrics, hybrid/Mamba cache accounting, DFlash2 integration, and runtime implementation used to diagnose capacity-limited admission. These projects are credited for the software; they did not author or endorse this recipe's conclusions.
- **Brandon M. Music / ShapleyMCG / TR3** — aligned `GLM-5.3-Flash-tr3-4bpw` checkpoint lineage used for the local matched-checkpoint control and already credited above for calibration, encoding, and runtime lineage.

The matched control was a locally retained aligned checkpoint corresponding to the runtime lineage. No immutable public Hub revision was recovered for that local copy, so the comparison is disclosed as a sequential local A/B rather than a fully revision-reproducible external benchmark. No aligned weights or benchmark outputs are redistributed.

### EvalPlus / HumanEval+

- **Jiawei Liu, Chunqiu Steven Xia, Yuyao Wang, and Lingming Zhang** — EvalPlus and HumanEval+.
- Repository: https://github.com/evalplus/evalplus
- Version used: EvalPlus 0.3.1; HumanEval+ v0.1.10
- License: Apache-2.0

```bibtex
@inproceedings{evalplus,
  title = {Is Your Code Generated by Chat{GPT} Really Correct? Rigorous Evaluation of Large Language Models for Code Generation},
  author = {Liu, Jiawei and Xia, Chunqiu Steven and Wang, Yuyao and Zhang, Lingming},
  booktitle = {Thirty-seventh Conference on Neural Information Processing Systems},
  year = {2023},
  url = {https://openreview.net/forum?id=1qvx610Cu7}
}
```

- **OpenAI** — original HumanEval benchmark, MIT licensed: https://github.com/openai/human-eval

### Gorilla / Berkeley Function-Calling Leaderboard

- **Shishir G. Patil, Tianjun Zhang, Xin Wang, Joseph E. Gonzalez, and Gorilla/BFCL contributors** — Gorilla and the Berkeley Function-Calling Leaderboard.
- Repository: https://github.com/ShishirPatil/gorilla
- Immutable commit used: `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`
- License: Apache-2.0

```bibtex
@article{patil2023gorilla,
  title={Gorilla: Large Language Model Connected with Massive APIs},
  author={Shishir G. Patil and Tianjun Zhang and Xin Wang and Joseph E. Gonzalez},
  year={2023},
  journal={arXiv preprint arXiv:2305.15334}
}
```

No HumanEval+, HumanEval, or BFCL dataset rows are redistributed by this repository. Only locally authored harnesses, a small model-registration patch, methods, and aggregate scores are included.

## Recipe

Recipe assembly, local qualification, benchmark harness, and public documentation: **Samuel Cardillo**.
