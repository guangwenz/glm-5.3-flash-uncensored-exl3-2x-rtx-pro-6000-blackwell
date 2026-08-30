# Provenance

All benchmark claims and launch defaults in this repository refer to this exact lineage.

## Target checkpoint

- Repository: `neko-legends/GLM-5.3-Flash-Uncensored-EXL3`
- Immutable revision: `1fac3dbe6269a399ce5378261cdf250fde706180`
- Hub pipeline: `image-text-to-text`
- Architecture: `Glm5NextForConditionalGeneration`
- Quantization: EXL3/TR3, 4-bit routed experts; other tensors BF16/FP16 as described by the checkpoint author
- Files: 106 total; 92 model shard files
- Exact total bytes represented by the Hub revision: 175,716,272,234
- Complete SHA-256 manifest: `manifests/model.sha256`
- ShapleyMCG license SHA-256: `9a354667162e40201fa556e29ae7a327cdb112eacaa8ef100106e6063635e28a`

The checkpoint card identifies its unpinned upstream chain as `zai-org/GLM-5.3-Flash` → `orcarouter/GLM-5.3-Flash-Uncensored-FP8` → this quantization. This recipe does not invent immutable revisions for those unpinned parent links.

## DFlash2 drafter

- Repository: `incoai/GLM-5.3-Flash-DFlash2`
- Immutable revision: `7d74cdd881ed7e32c31175984a67823127b66cfe`
- Architecture: `DFlash2DraftModel`
- `model.safetensors` SHA-256: `8931dc522be0aa31760a7463f8d2f8044fa3e6d40be2e87aa08e9fd17bfd6683`
- Total revision bytes: 2,342,175,855
- License: CC BY-NC-ND 4.0
- Complete SHA-256 manifest: `manifests/dflash2.sha256`

This older immutable revision is intentional: it is the exact checkpoint named by the qualified runtime image's embedded provenance and the one used during local qualification. Do not silently substitute the repository's newer branch tip.

## Runtime image

- Image: `verdictai/glm53-flash-exl3-k4:r19-sm120-tp2-ep2-dcp2-v84-dflash2`
- Digest: `sha256:0f1cdcc8891f1cc3a444121eb61d366289a1cbba285f0892dcbb24bc94961692`
- Declared author: Brandon M. Music
- Declared source: https://github.com/brandonmmusic-max/glm-5.3-flash-exl3-4bpw
- Public release commit first binding this exact image digest: `bd5321c1cfd4b8d352ef380e3158c64886039d03`
- Declared image license: `LicenseRef-ShapleyMCG-1.0`
- Embedded release: `r19-sm120-tp2-ep2-dcp2-v84-dflash2`
- Embedded provenance copied without modification to `manifests/runtime-image-provenance.json`
- Embedded provenance SHA-256 / OCI fingerprint: `cf4b00958987cc50f94641592b1a8d74874adb4d671861ce12dd5e8f2907d907`

The image's own target labels name the aligned build-time checkpoint `brandonmusic/GLM-5.3-Flash-tr3-4bpw`; they do **not** prove the uncensored checkpoint identity. This recipe deliberately substitutes the separately pinned `neko-legends` target at the read-only `/model` mount. That target is bound by its own 106-file manifest and qualified launch evidence, while the image record is preserved as aligned-build runtime lineage.

Important embedded runtime identities include:

- `local-inference-lab/vllm` commit `6dc2f516688fe6f84c6994dcd20fddf296853a6c`, integration tree `174c789e09984049d0d53b261024460ca5e9c449`
- vLLM package `0.26.1rc0+infernal.invocation.cu133.r19.vllm174c789.b12x12c4263`
- B12x commit `36bce2c1552ba2d47dc09f20a6f64fbfc8ec4ff8`, integration tree `12c426322cc5d239023b57a4bd5ab0e60c4302e0`
- ExLlamaV3 fork commit `704aefd743b390af4bd0fb429d1906f9b964c7d8`
- DFlash reference `local-inference-lab/vllm@e7097feb6fcdf57911cd68884420af2d80600dd7`
- PyTorch 2.13.0 lineage commit `cf30153c4c131c8164ee7798e5022d810682e2cb`
- TorchVision commit `8fb87713a24951e639c494b0f2a8a81b5f8e33a6`
- FlashInfer fork commit `1ac6942776b383c6b03c7a5805a22e72a3e3349f`
- DeepGEMM commit `a6b593d2826719dcf4892609af7b84ee23aaf32a`
- InstantTensor commit `49b4010afc1cae0441e71fe0b0bffc24fa05e932`
- LMCache commit `a128b2e286ebb3556cb43124149e600ff99fe481`, integration tree `e045d729bc5c4c63a40e13d032f42923de97812f`
- NCCL canonical commit `fb6f40999a2a9e63104d4ae4a84118bce61528f8`
- xGrammar commit `2ea71da4ccb997a06928c9fb69b99f330da56697`
- CUDA 13.3 runtime profile
- NVIDIA foundation image `nvcr.io/nvidia/pytorch:26.07-py3@sha256:2140e699b3beaf7f96a0081fd9c9406bc3832b435cdb60dfa2d261f7d2f34a1c`
- parent image digest `sha256:6a0a4814b1e7aaa286a40ce8959cc9db2431b601a98a5be95b8020c748e0f5ea`

The recipe does not redistribute this image. Although the image carries extensive labels and an embedded provenance manifest, this repository has not independently rebuilt every layer from source. The public source commit contains launchers and receipts but no complete Dockerfile/build context; `local-inference.docker.commit=54a4e2da5e976230864573c0d79bb0eb777dd382` has no associated repository URL; the `klc` parent source is undisclosed; and the mutable `voipmonitor/vllm` runtime base is identified only by a local image ID. Pull and use the image only after reviewing its registry and upstream terms.

## Benchmark toolchain

- EvalPlus: 0.3.1
- HumanEval+: v0.1.10
- Original evaluator base: `python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6`
- Exact successful evaluator package set: `benchmarks/requirements-evalplus.txt`
- Gorilla/BFCL: `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`

## Qualified launch profile

- 2× RTX PRO 6000 Blackwell Workstation Edition 96 GB
- TP2, EP2, DCP2 with A2A DCP communication
- B12x sparse MLA attention and MoE backend
- NVFP4 DSA/MLA KV cache with pinned calibration file inside the image
- maximum model length 262,144
- chunked prefill with 1,024 maximum batched tokens
- maximum sequences 8
- GPU memory utilization 0.979
- prefix caching disabled
- DFlash2 probabilistic draft, standard rejection sampling, depth 7, draft TP2
- one image per prompt; video zero
- multimodal template `/opt/glm53/chat_template.multimodal.jinja`
- GLM45 reasoning parser and GLM47 tool parser

## Tested host

- Ubuntu 24.04
- NVIDIA driver 590.48.01
- Docker 29.1.3
- two explicitly selected RTX PRO 6000 Blackwell 96 GB cards
- an unrelated RTX 5090 was present but excluded

The exact private GPU UUIDs, usernames, host paths, addresses, and credentials are intentionally not published.
