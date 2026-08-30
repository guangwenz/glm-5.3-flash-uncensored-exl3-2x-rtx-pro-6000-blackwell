# Troubleshooting

## Preflight says the wrong GPU was selected

`GPU_DEVICES` uses physical host indices. Run:

```bash
nvidia-smi --query-gpu=index,uuid,name,memory.total,memory.free,pci.bus_id --format=csv
```

Select exactly two RTX PRO 6000 Blackwell 96 GB cards. Do not copy indices from another workstation. The recipe fails closed if a selected device is a 5090, RTX 6000 Ada, A6000, or another model.

## Insufficient free VRAM

Stop other inference containers and GPU applications. The qualified profile checks for at least 88,000 MiB free on each selected card before startup. Desktop graphics allocations are acceptable only if this threshold remains available.

Read-only diagnostics:

```bash
nvidia-smi
nvidia-smi topo -m
nvidia-smi topo -p2p r
docker ps
```

Do not make IOMMU, ACS, driver, firmware, or PCIe changes merely because peer access differs from another host. The qualified runtime uses a PCIe all-reduce path and those changes are platform-specific and potentially disruptive.

## Hash verification takes a long time

This is intentional. `scripts/preflight.sh` verifies the complete 106-file target manifest and the DFlash2 manifest, reading about 178 GB. A shard count proves shape, not identity.

## Hugging Face returns 401/403

The target checkpoint is gated. Confirm approval and authentication:

```bash
hf auth whoami
hf download neko-legends/GLM-5.3-Flash-Uncensored-EXL3 \
  --revision 1fac3dbe6269a399ce5378261cdf250fde706180 \
  --include README.md
```

Do not publish your token or store it in this recipe's `.env`.

## Container image pull fails

The exact digest must be available from the `verdictai` registry namespace. The recipe does not fall back to a mutable tag or a different image. Authenticate to Docker Hub if the registry requires it, then retry `docker pull` with the exact reference in `scripts/defaults.sh`.

## Startup is slow

The service loads roughly 176 GB of target weights plus the drafter and compiles/caches kernels. Follow:

```bash
docker logs -f glm53-flash-uncensored-exl3
```

Do not reduce context, disable vision, substitute the drafter, or alter quantization and still claim the published benchmark lineage.

## OOM during KV allocation

Confirm both cards are the 96 GB Blackwell workstation model and no competing workload started after preflight. The qualified setting is `GPU_MEMORY_UTILIZATION=0.979`; increasing it is rejected. Reducing it may fail to provide the 262,144-token contract.

## API is unreachable remotely

The safe default binds only to `127.0.0.1`. For trusted remote access, set a specific LAN or Tailnet IPv4 address. Prefer an authenticated LiteLLM/reverse-proxy boundary. Never expose this unauthenticated uncensored model directly to the public Internet.

## Tool calls are unreliable

The official BFCL results show significant weakness in multiple/parallel tool selection. Validate tool names and JSON arguments, bound outputs, retry malformed calls, require human approval for irreversible actions, and do not assume the model is a reliable autonomous operator.
