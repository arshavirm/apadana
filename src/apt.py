import subprocess


class Apt:
    @staticmethod
    def run(command) -> dict:
        result = subprocess.run(command, text=True, capture_output=True)

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }


def get_installed_packages():
    output = Apt.run(["apt", "list", "--installed"])["stdout"]

    packages = []

    for line in output.splitlines():
        if not line or line.startswith("Listing..."):
            continue

        package_info, version, *_ = line.split()

        name = package_info.split("/")[0]

        packages.append(
            {
                "name": name,
                "version": version,
            }
        )

    packages.sort(key=lambda p: p["name"].lower())
    return packages


def get_package_info(pkg_name):
    output = Apt.run(["apt", "show", pkg_name])["stdout"]

    return output
