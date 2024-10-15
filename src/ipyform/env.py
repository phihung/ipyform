import os

IN_VSCODE = bool(os.getenv("VSCODE_PID"))
IN_COLAB = bool(os.getenv("COLAB_RELEASE_TAG"))
