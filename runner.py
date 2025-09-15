
import os, sys, importlib, importlib.util, types
from threading import Thread

def _try_import(module_name: str):
    try:
        return importlib.import_module(module_name)
    except Exception as e:
        print(f"[runner] import failed for '{module_name}': {e}")
        return None

def _spec_import_from_path(path: str):
    try:
        spec = importlib.util.spec_from_file_location(os.path.splitext(os.path.basename(path))[0], path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore
        return mod
    except Exception as e:
        print(f"[runner] spec import failed for '{path}': {e}")
        return None

def _looks_like_bot(mod: types.ModuleType):
    return (
        hasattr(mod, "app") and
        hasattr(mod, "main_bot_loop") and callable(getattr(mod, "main_bot_loop")) and
        hasattr(mod, "place_order") and callable(getattr(mod, "place_order")) and
        hasattr(mod, "close_position") and callable(getattr(mod, "close_position"))
    )

def _autodetect_bot_module():
    exclude = {"runner.py", "guard_wrapper.py", "render.yaml", "requirements.txt", ".env.sample", "README.txt"}
    for name in os.listdir("."):
        if name.endswith(".py") and name not in exclude:
            mod = _spec_import_from_path(os.path.abspath(name))
            if mod and _looks_like_bot(mod):
                print(f"[runner] autodetected bot module: {name}")
                return mod
    return None

def load_userbot():
    module_name = os.getenv("BOT_MODULE", "bot").replace(".py", "")
    mod = _try_import(module_name)
    if mod and _looks_like_bot(mod):
        print(f"[runner] loaded bot module via env: {module_name}")
        return mod
    print("[runner] env-based import failed or missing attributes; trying autodetect...")
    mod = _autodetect_bot_module()
    if mod:
        return mod
    raise ModuleNotFoundError(
        "Could not load bot module. Set BOT_MODULE env var to your file name without .py "
        "or rename your main file to bot.py"
    )

def main():
    userbot = load_userbot()
    try:
        userbot.keep_alive = lambda: None
    except Exception:
        pass

    from guard_wrapper import attach_guard
    attach_guard(userbot)

    t = Thread(target=userbot.main_bot_loop, daemon=True)
    t.start()

    port = int(os.getenv("PORT", "10000"))
    userbot.app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
