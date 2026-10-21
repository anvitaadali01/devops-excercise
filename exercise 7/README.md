# Exercise 7: Jenkins CI Automation

> The requested notes file, `7-Jenkins-CI-Automation.md`, was not present in the repository or workspace when this was prepared. This exercise follows the requirements supplied in the task; compare with the original notes if they become available.

## Continuous Integration

Continuous Integration (CI) is the practice of frequently integrating small code changes into a shared repository and automatically verifying them. A CI pipeline checks out the current revision, verifies its environment, installs dependencies, runs automated tests, and reports failures early. This shortens feedback cycles, catches regressions near the change that introduced them, and provides a repeatable record of what was tested. CI does not guarantee software is defect-free; it makes agreed checks consistent and visible.

## Jenkins concepts

- **Job:** a configured unit of work, such as this Pipeline job.
- **Build:** one execution of a job against a particular revision and parameters, with a result and console log.
- **Pipeline:** the versioned workflow described by a `Jenkinsfile`; named stages make checkout, tests, and verification visible.
- **Plugin:** an extension that adds integrations or functionality. The Git and Pipeline plugins are needed for the SCM workflow; the setup wizard can install recommended plugins.
- **Node/agent:** the machine or executor that runs job steps. This pipeline expects an agent labeled `linux-python` with Python 3.10+, Git, a POSIX shell, and access to the configured repository. Docker is optional and required only if the image-build parameter is enabled.

## Run locally

From the repository root in Windows PowerShell:

```powershell
$project = (Resolve-Path '.\Ex 7').Path
$venv = Join-Path $project '.venv'
py -m venv $venv
& "$venv\Scripts\python.exe" -m pip install -r "$project\requirements.txt"
& "$venv\Scripts\python.exe" -m unittest discover -s $project -p 'test_*.py' -v
& "$venv\Scripts\python.exe" "$project\app.py" --name 'Jenkins CI'
```

The application prints `Hello, Jenkins CI!`. The requirements file documents that the app and tests use only the standard library, so there are no third-party packages to download. The `.venv` is inside `Ex 7` and ignored by its `.gitignore`.

On Linux or macOS, run from the repository root:

```sh
python3 -m venv 'Ex 7/.venv'
'Ex 7/.venv/bin/python' -m pip install -r 'Ex 7/requirements.txt'
'Ex 7/.venv/bin/python' -m unittest discover -s 'Ex 7' -p 'test_*.py' -v
'Ex 7/.venv/bin/python' 'Ex 7/app.py' --name 'Jenkins CI'
```

## Build and run the Docker image

Docker is optional for the default CI pipeline. If Docker Desktop is running with Linux containers, build and run from the repository root:

```powershell
docker build --tag ex7-ci-demo '.\Ex 7'
docker run --rm ex7-ci-demo --name 'Jenkins CI'
```

Expected output: `Hello, Jenkins CI!`. The Dockerfile uses Python 3.12, installs the dependency declaration, copies the app, and runs it as a non-root user.

## Install Jenkins with Docker

First inspect whether a container named `jenkins` already exists. Do not remove it or its data as part of setup:

```powershell
docker ps -a --filter 'name=^/jenkins$'
```

If it is running, use that instance. If it exists but is stopped, inspect it and start it with `docker start jenkins` if it is the instance you intend to use. Only create a new container if no `jenkins` container exists:

```powershell
docker run -d --name jenkins -p 8080:8080 -p 50000:50000 jenkins/jenkins:lts
docker ps -a
```

Wait for startup, then retrieve the generated initial administrator password from the host:

```powershell
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

The interactive equivalent is:

```powershell
docker exec -it jenkins bash
cat /var/jenkins_home/secrets/initialAdminPassword
exit
```

Open <http://localhost:8080/> and enter the password generated for your own Jenkins instance. Keep it private; do not put it in source files, logs, or screenshots. Complete the setup wizard and install recommended plugins, including Git and Pipeline support if they were not selected.

## Configure and run the Pipeline

The repository URL is `https://github.com/ANSHIKAAGRAWAL1/devops.git`. The current designated branch is `main`, and the Jenkinsfile path is `Ex 7/Jenkinsfile`.

1. In Jenkins, select **New Item**, enter a job name such as `Exercise 7 CI`, choose **Pipeline**, then select **OK**.
2. Under **Pipeline**, choose **Pipeline script from SCM**, select **Git**, and enter the repository URL above.
3. Set the branch specifier to `*/main` and **Script Path** to `Ex 7/Jenkinsfile`.
4. Save and select **Build Now**. Open the build and **Console Output** to follow the stages.

For a private repository, create a Jenkins credential under **Manage Jenkins > Credentials** and select its credential ID in the Git SCM configuration. Prefer an SSH private-key credential or narrowly scoped access token stored only in Jenkins credentials. Never embed credentials in repository URLs, the Jenkinsfile, or shell commands. Public-repository checkout does not need a credential.

The pipeline uses `checkout scm`, so Jenkins checks out the configured repository and branch into its actual workspace. Its commands run inside the checked-out `Ex 7` folder; it does not use a machine-specific local path.

## Pipeline stages and Docker security

The `Jenkinsfile` checks out the configured source, verifies Python 3.10+ and Git, creates an isolated `.venv-ci` and installs the declared requirements, runs the non-interactive `unittest` suite, compiles the app/tests, and checks the app's output. The venv and Python cache are removed after the run. Required-command failures fail the build. The optional `BUILD_DOCKER_IMAGE` parameter is disabled by default; enable it only on a suitable Docker-capable agent.

The Docker-based Jenkins controller does not automatically have access to the host Docker Engine. The default CI stages need no Docker socket. For the optional image stage, configure an access-controlled Linux agent labeled `linux-python` with Python, Git, a POSIX shell, Docker CLI, and authorized Engine access. Docker socket access, including membership in the Docker group, effectively grants host-administrator privileges. Do not mount the host socket into the Jenkins controller or make it world-writable simply to get a green build. Prefer a dedicated agent or controlled remote builder and assess the access it grants. The optional stage removes its uniquely tagged image after the build.

## Verify and clean up

Locally, confirm tests with the `unittest` command in the setup section. In Jenkins, verify that each required stage is green and inspect the console log. A green result demonstrates only that these included tests passed on that revision; it does not prove behavior beyond their coverage.

Stop Jenkins while preserving its container with:

```powershell
docker stop jenkins
```

Restart the same instance with `docker start jenkins`. Do not use `docker rm -v` unless you deliberately intend to delete Jenkins data. This exercise does not remove an existing Jenkins container. Remove the app image when no longer needed with `docker image rm ex7-ci-demo`.

## Troubleshooting

- Docker cannot connect: start Docker Desktop, ensure it uses Linux containers, and check `docker info` before creating Jenkins or building the app image.
- Port 8080 or 50000 is already in use: inspect `docker ps -a` and local port use; do not delete an existing Jenkins container. If creating a separate instance, use unused host ports and browse to the host-side 8080 mapping.
- Jenkins is still starting: inspect `docker logs jenkins` and wait before retrieving the initial password.
- Jenkins cannot find the Jenkinsfile: verify the configured branch contains it and the script path is exactly `Ex 7/Jenkinsfile`.
- Python is missing or too old on the agent: install/configure Python 3.10+ there and verify `PATH`; the controller's Python is not automatically available to agents.
- Private repository checkout fails: configure the appropriate Jenkins credential in SCM settings and verify access without printing the secret.
- The optional image stage fails: check the agent's Docker CLI and authorized Engine access. The standard test pipeline intentionally needs no Docker-in-Docker or host socket.

## Submission screenshots

See [`screenshots/README.md`](screenshots/README.md) for the requested evidence list. Capture your own dashboard, job configuration, successful build, console output, and tests after running Jenkins. No screenshots are included or claimed here.
