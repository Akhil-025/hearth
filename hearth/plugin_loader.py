import importlib

def load_plugins():
    plugins = [
        "hearth.insight.indexer",
        "hearth.ritual.pulse",
        "hearth.sentience.reflection"
    ]
    for p in plugins:
        try:
            importlib.import_module(p).register()
        except Exception as e:
            print(f"[HEARTH] Failed to load {p}: {e}")
