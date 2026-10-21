import sys

import docker
from docker.errors import APIError, DockerException


IMAGE_TAG = "flask-apparmor:latest"
PROFILE_NAME = "flask-apparmor"
PYTHON = "/usr/local/bin/python3.11"


def display_result(label, result):
    output = result.output
    if isinstance(output, tuple):
        stdout, stderr = output
        output = (stdout or b"") + (stderr or b"")
    if isinstance(output, bytes):
        output = output.decode("utf-8", errors="replace")
    print(f"{label}: exit_code={result.exit_code}")
    print(output.rstrip() or "(no output)")


def main():
    client = None
    container = None
    exit_status = 0
    try:
        client = docker.from_env()
        client.images.get(IMAGE_TAG)
        container = client.containers.create(
            IMAGE_TAG,
            command=[PYTHON, "-c", "import time; time.sleep(300)"],
            security_opt=[f"apparmor={PROFILE_NAME}"],
        )
        container.start()
        container.reload()
        active_profile = container.attrs.get("AppArmorProfile", "")
        print(f"AppArmorProfile: {active_profile or '(not reported)'}")
        if active_profile != PROFILE_NAME:
            raise RuntimeError(
                f"Expected active profile {PROFILE_NAME!r}, got {active_profile!r}; "
                "restricted-action results would not verify this profile."
            )

        passwd_command = [
            PYTHON,
            "-c",
            "print(open('/etc/passwd', encoding='utf-8').read())",
        ]
        try:
            passwd_result = container.exec_run(passwd_command, demux=False)
            display_result("Read /etc/passwd", passwd_result)
            output = passwd_result.output
            if isinstance(output, bytes):
                output = output.decode("utf-8", errors="replace")
            if passwd_result.exit_code == 0:
                print("UNEXPECTED: /etc/passwd was readable.")
                exit_status = 1
            elif "PermissionError" in output and "Errno 13" in output:
                print(
                    "Read was denied with EACCES. The file is world-readable in "
                    "the image and the process is non-root; confirm AppArmor "
                    "attribution in the Linux host audit log."
                )
            else:
                print(
                    "This failure is not identified as an AppArmor read denial; "
                    "check the output and host audit log."
                )
                exit_status = 1
        except APIError as error:
            print(f"Read /etc/passwd: Docker exec API error: {error}")
            exit_status = 1

        bash_check = container.exec_run(
            [PYTHON, "-c", "import os; print(os.path.isfile('/bin/bash'))"]
        )
        bash_exists = bash_check.exit_code == 0 and b"True" in bash_check.output
        print(f"/bin/bash present in image: {bash_exists}")
        if not bash_exists:
            print("Cannot test the execute restriction: /bin/bash is missing.")
            exit_status = 1
        else:
            try:
                bash_result = container.exec_run(
                    ["/bin/bash", "-c", "echo bash-executed"], demux=False
                )
                display_result("Execute /bin/bash", bash_result)
                output = bash_result.output
                if isinstance(output, bytes):
                    output = output.decode("utf-8", errors="replace")
                if bash_result.exit_code == 0:
                    print("UNEXPECTED: /bin/bash executed successfully.")
                    exit_status = 1
                elif "permission denied" in output.lower() or "apparmor" in output.lower():
                    print(
                        "Execution was rejected; confirm the corresponding "
                        "AppArmor DENIED event in the Linux host audit log."
                    )
                else:
                    print(
                        "The failure is not identified as an AppArmor execute "
                        "denial; check the output and host audit log."
                    )
                    exit_status = 1
            except APIError as error:
                message = str(error)
                print(f"Execute /bin/bash: Docker exec API error: {message}")
                if "permission denied" not in message.lower() and "apparmor" not in message.lower():
                    print("The API error does not identify an AppArmor denial.")
                    exit_status = 1

        print(
            "AppArmor audit records must be checked on the Linux Docker host "
            "to attribute kernel denials conclusively."
        )
    except (DockerException, RuntimeError, KeyError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        exit_status = 1
    finally:
        if container is not None:
            try:
                container.stop(timeout=5)
            except DockerException as error:
                print(f"Container stop failed: {error}", file=sys.stderr)
                exit_status = 1
            try:
                container.remove(force=True)
                print("Test container removed.")
            except DockerException as error:
                print(f"Container removal failed: {error}", file=sys.stderr)
                exit_status = 1
        if client is not None:
            client.close()
    return exit_status


if __name__ == "__main__":
    raise SystemExit(main())
