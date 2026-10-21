import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import docker
from docker.errors import DockerException


IMAGE_TAG = "flask-apparmor:latest"
PROFILE_NAME = "flask-apparmor"
PROJECT_DIR = Path(__file__).resolve().parent
EXPECTED_RESPONSE = (
    "Hello, this is a secure Flask application running inside a Docker container!"
)


def build_image(client):
    image, build_output = client.images.build(
        path=str(PROJECT_DIR), tag=IMAGE_TAG, rm=True
    )
    for entry in build_output:
        if "error" in entry:
            raise RuntimeError(entry["error"])
    return image


def check_endpoint(container):
    port_bindings = container.attrs["NetworkSettings"]["Ports"]["5000/tcp"]
    if not port_bindings:
        raise RuntimeError("Docker did not publish container port 5000.")
    host_port = port_bindings[0]["HostPort"]
    url = f"http://127.0.0.1:{host_port}/"

    for attempt in range(20):
        try:
            with urlopen(url, timeout=2) as response:
                body = response.read().decode("utf-8")
                if response.status != 200 or body != EXPECTED_RESPONSE:
                    raise RuntimeError(
                        f"Unexpected Flask response: HTTP {response.status}, {body!r}"
                    )
                print(f"Flask endpoint: HTTP {response.status}, exact response verified.")
                return
        except (OSError, URLError):
            if attempt == 19:
                raise RuntimeError("Flask endpoint did not become ready.")
            time.sleep(0.5)


def main():
    client = None
    container = None
    result = 0
    try:
        client = docker.from_env()
        image = build_image(client)
        print(f"Built image: {image.tags}")
        container = client.containers.create(
            image.id,
            ports={"5000/tcp": None},
            security_opt=[f"apparmor={PROFILE_NAME}"],
        )
        container.start()
        container.reload()
        apparmor_profile = container.attrs.get("AppArmorProfile", "")
        security_options = container.attrs.get("HostConfig", {}).get("SecurityOpt")
        print(f"Container: {container.short_id} ({container.status})")
        print(f"AppArmorProfile: {apparmor_profile or '(not reported)'}")
        print(f"HostConfig.SecurityOpt: {security_options}")
        if apparmor_profile != PROFILE_NAME:
            raise RuntimeError(
                f"Expected active AppArmor profile {PROFILE_NAME!r}; "
                f"Docker reports {apparmor_profile!r}."
            )
        check_endpoint(container)
    except (DockerException, RuntimeError, KeyError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        result = 1
    finally:
        if container is not None:
            try:
                container.stop(timeout=5)
                print("Container stopped.")
            except DockerException as error:
                print(f"Could not stop container cleanly: {error}", file=sys.stderr)
                result = 1
                try:
                    container.remove(force=True)
                    print("Container force-removed after stop failure.")
                except DockerException as cleanup_error:
                    print(f"Container cleanup failed: {cleanup_error}", file=sys.stderr)
        if client is not None:
            client.close()
    return result


if __name__ == "__main__":
    raise SystemExit(main())
