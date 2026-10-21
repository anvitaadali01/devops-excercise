# Exercise 5: Docker Security with AppArmor and Python

## Contents

- `app.py`: Flask endpoint on `0.0.0.0:5000`.
- `Dockerfile`: Python 3.11 image, Flask, a non-root runtime user, and Bash installed so the execute-denial test can distinguish a policy denial from a missing binary.
- `my-apparmor-profile`: enforce-mode profile named `flask-apparmor`.
- `apply_apparmor.py`: builds the image with the Docker SDK, starts a profiled container, reports the effective profile/security options, checks the exact HTTP response, and stops the container.
- `test_restricted_actions.py`: attempts a `/etc/passwd` read and `/bin/bash` execution in a profiled test container, reports exit codes/output, and removes the container in all cases.
- `requirements.txt`: Flask and the Docker SDK for Python.

## Requirements and installation

The Docker SDK scripts run on a machine with Python 3.10 or newer, the Docker SDK, and access to a Docker Engine. AppArmor enforcement must be available and enabled on the Linux host running that Engine. Loading a host profile requires administrator privileges.

Install the Python dependencies in a virtual environment outside this assignment directory. For example, on Linux:

```sh
python3 -m venv /tmp/ex5-venv
. /tmp/ex5-venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows PowerShell, use `py -m venv "$env:TEMP\ex5-venv"`, activate with `& "$env:TEMP\ex5-venv\Scripts\Activate.ps1"`, and then run `python -m pip install -r requirements.txt`.

## Load the AppArmor profile

Run these commands on the Linux Docker host, from this directory:

```sh
sudo apparmor_parser -r -W my-apparmor-profile
sudo aa-status
```

Confirm that `flask-apparmor` is loaded in enforce mode before starting a container. Reload after editing the profile. Docker Desktop on Windows does not make the Windows host an AppArmor host; the profile must be loaded in the Linux environment that runs the Docker Engine. If Docker Desktop's Linux VM does not expose custom AppArmor profiles, use a compatible Linux host or VM instead.

## Build and run

```sh
docker build -t flask-apparmor:latest .
docker run --rm -p 5000:5000 --security-opt apparmor=flask-apparmor flask-apparmor:latest
```

In another terminal, request `http://127.0.0.1:5000/`. The response body should be exactly:

```text
Hello, this is a secure Flask application running inside a Docker container!
```

## Docker SDK automation and restricted-action tests

With the profile loaded and dependencies installed, run:

```sh
python apply_apparmor.py
python test_restricted_actions.py
```

The first script builds `flask-apparmor:latest`, publishes the Flask port on a dynamically assigned host port, checks the response and Docker's inspected `AppArmorProfile`/`HostConfig.SecurityOpt`, then stops the container. The second script expects that image to exist and uses the same profile. Both scripts clean up their containers if an error occurs.

`/etc/passwd` is normally world-readable, and the image runs as UID 10001. A `PermissionError` with `Errno 13` therefore indicates an access-control denial rather than the file's ordinary Unix mode denying this user. The test reports the actual exit code and output, but definitive attribution requires checking the Linux host's kernel audit log for an AppArmor `DENIED` record. A successful read is a test failure.

The Dockerfile deliberately installs `/bin/bash`; the test checks that the file exists before trying to execute it. An exit code or API error alone is not proof of AppArmor enforcement: a missing executable, profile attachment failure, or other runtime error must be reported as such. Confirm a matching AppArmor `DENIED` audit record for a conclusive execution-denial result.

## Profile scope and compatibility

The profile allows execution only of `/usr/local/bin/python3.11`, and allows read access to the application source and Python 3.11 standard/site-package files. Shared-library mappings and the dynamic-loader cache are permitted because Python and Flask need them at startup. System CA certificates are readable for compatibility with Python TLS clients. The application directory is read-only to the process. Sensitive account/SSH/sudo configuration and `/var/**` are explicitly denied, and `sys_admin` is explicitly denied; unlisted capabilities and executable paths have no allow rule in this enforce-mode profile.

Flask needs TCP sockets to accept HTTP requests, so IPv4 and IPv6 stream sockets are allowed. AppArmor's network rule here does not constrain TCP port or peer addresses; Docker port publishing determines host exposure. Other network classes have no allow rule. The Python 3.11 interpreter/library paths match the selected official image family and must be checked against the built image if the base image changes. These rules may need narrowly scoped adjustment if the selected image's loader or libraries differ; do not remove denials merely to make a test pass.

## Troubleshooting

- `apparmor_parser` is missing or `aa-status` reports AppArmor disabled: use a Linux host with AppArmor enabled and load the profile there.
- Docker reports `apparmor is not supported`, `profile not found`, or a different `AppArmorProfile`: the profile is not active on the Docker Engine host. Do not interpret restricted-action results as proof of enforcement.
- Docker cannot connect to its daemon: start/configure the Docker Engine and retry.
- Image build or app startup fails: check the build output and confirm `/usr/local/bin/python3.11` and the Python 3.11 library paths in the image match the profile.
- `/etc/passwd` is readable or Bash executes: inspect the active profile and host audit log; make sure the loaded profile is the current version and is in enforce mode.
- A failed exec says `executable file not found`: that is not an AppArmor denial. This image installs Bash specifically to prevent that ambiguity.
- For kernel-side evidence on Linux, inspect the system journal or audit log (for example, `sudo journalctl -k | grep -i apparmor` or `sudo ausearch -m AVC,USER_AVC -ts recent` where auditd is installed).

## Assignment questions and answers

The supplied task did not include the instructor's exact five question wordings. These answers address the five requested security topics; align their wording with the original handout if it differs.

1. **What is AppArmor?** A Linux kernel security module that confines programs with path-based profiles defining permitted resources and operations.
2. **How does the profile protect this application?** In enforce mode it limits execution to the Python interpreter, makes `/app` read-only, denies selected sensitive `/etc` and `/var` paths, allows only the socket class needed for HTTP, and denies `sys_admin`.
3. **Why is TCP network access allowed?** Flask must create and accept TCP sockets to serve HTTP. The profile permits TCP socket operations but does not itself limit ports or peers; the Docker port mapping controls exposure.
4. **How should restricted actions be verified?** Attempt the operations inside a container and record exit status/output, verify the inspected container profile, then match the denials to AppArmor `DENIED` audit records on the Linux host. A command failure without that context may have another cause.
5. **Why deny `sys_admin` and restrict `/etc` and `/var`?** `sys_admin` enables broad host-relevant administrative operations; sensitive account/SSH/sudo files and variable data are not needed by this service, so denying access reduces the impact of a compromised application.
