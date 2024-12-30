import datetime
import os
import requests
import subprocess

openrgb_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "assets", "OpenRGB.AppImage")
)

pip_dependencies = ["black", "psutil", "pyinstaller", "PyQt5"]


def install_pip_deps():
    print("  Installing PIP packages...")
    command = ["pip", "install"]
    command.extend(pip_dependencies)
    subprocess.run(command, check=True)
    print("  Dependencies installed")


def get_openrgb():
    print("  Installing OpenRGB...")

    url = f"https://api.github.com/repos/Emiliopg91/OpenRGB/releases/latest"
    response = requests.get(url)

    file_mod_date = (
        datetime.datetime.fromtimestamp(os.path.getmtime(openrgb_path))
        if os.path.exists(openrgb_path)
        else None
    )

    if response.status_code == 200:
        release_data = response.json()
        data = [
            asset
            for asset in release_data["assets"]
            if asset["name"].endswith(".AppImage")
        ]
        if len(data) > 0:
            asset = data[0]
            if file_mod_date is None or file_mod_date < datetime.datetime.strptime(
                asset["created_at"], "%Y-%m-%dT%H:%M:%SZ"
            ):
                print("    Downloading dependency...")
                url = asset["browser_download_url"]

                response = requests.get(url, stream=True)
                response.raise_for_status()

                with open(openrgb_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                os.chmod(openrgb_path, 0o755)

                print("    Dependency updated")
            else:
                print("    Dependency up to date")
        else:
            raise FileNotFoundError("No URL published for OpenRGB")
    else:
        raise Exception(f"Error getting latest release: {response.status_code}")


print("Installing dependencies...")
install_pip_deps()
get_openrgb()
