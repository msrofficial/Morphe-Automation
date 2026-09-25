"""Domain models for Morphe-Automation v2 (independent layer)."""
from dataclasses import dataclass, field


@dataclass
class AppSpec:
    app_name: str
    source: str
    arches: list = field(default_factory=lambda: ["universal"])
    build_modes: list = field(default_factory=lambda: ["apk"])
    version: str = "auto"
    dpi: str = "nodpi"
    include_stock: str = "merged"
    enable_update_checks: bool = False
    module_prop_name: str = ""
    patcher_args: str = ""


@dataclass
class BuildTarget:
    app: AppSpec
    arch: str
    mode: str  # apk | module

    @property
    def key(self) -> str:
        return f"{self.app.app_name}|{self.app.source}|{self.arch}|{self.mode}"


@dataclass
class BuildResult:
    target: BuildTarget
    output: str = ""
    version: str = ""
    ok: bool = False
    error: str = ""


def targets_from_unified(data: dict, only_app="", only_source="", only_arch="", only_mode=""):
    out = []
    for a in data.get("apps", []):
        if only_app and a.get("app_name") != only_app:
            continue
        if only_source and a.get("source") != only_source:
            continue
        spec = AppSpec(
            app_name=a.get("app_name", ""),
            source=a.get("source", ""),
            arches=a.get("arches", ["universal"]),
            build_modes=a.get("build_modes", ["apk"]),
            version=a.get("version", "auto"),
            dpi=a.get("dpi", "nodpi"),
            include_stock=a.get("include_stock", "merged"),
            enable_update_checks=bool(a.get("enable_update_checks", False)),
            module_prop_name=a.get("module_prop_name", ""),
            patcher_args=a.get("patcher_args", ""),
        )
        for arch in spec.arches:
            if only_arch and arch != only_arch:
                continue
            for mode in spec.build_modes:
                if only_mode and mode != only_mode:
                    continue
                out.append(BuildTarget(app=spec, arch=arch, mode=mode))
    return out
