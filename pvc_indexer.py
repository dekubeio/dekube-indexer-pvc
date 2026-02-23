"""PVC indexer — pre-registers PersistentVolumeClaim and workload PVC references."""

from h2c import ConverterResult, IndexerConverter  # pylint: disable=import-error  # h2c resolves at runtime

_WORKLOAD_KINDS = ("DaemonSet", "Deployment", "Job", "StatefulSet")


def _track_pvc(claim, ctx):
    """Track a PVC claim. On first run, also register in config for host_path mapping."""
    if not claim:
        return
    ctx.pvc_names.add(claim)
    if ctx.first_run and claim not in ctx.config.get("volumes", {}):
        ctx.config.setdefault("volumes", {})[claim] = {"host_path": claim}


class PVCIndexer(IndexerConverter):  # pylint: disable=too-few-public-methods  # contract: one class, one method
    """Pre-register PVCs in config so volume conversion can resolve host_path on first run."""
    name = "pvc"
    kinds = ["PersistentVolumeClaim"]

    def convert(self, _kind, manifests, ctx):
        """Index PVC manifests and scan workloads for volume claim references."""
        # Register explicit PVC manifests
        for m in manifests:
            claim = m.get("metadata", {}).get("name", "")
            _track_pvc(claim, ctx)
        # Scan workload manifests for volumeClaimTemplates and persistentVolumeClaim refs
        for wl_kind in _WORKLOAD_KINDS:
            for m in ctx.manifests.get(wl_kind, []):
                spec = m.get("spec") or {}
                for vct in spec.get("volumeClaimTemplates") or []:
                    _track_pvc(vct.get("metadata", {}).get("name", ""), ctx)
                pod_vols = ((spec.get("template") or {}).get("spec") or {}).get("volumes") or []
                for v in pod_vols:
                    pvc = v.get("persistentVolumeClaim") or {}
                    _track_pvc(pvc.get("claimName", ""), ctx)
        return ConverterResult()
