# Exercise 9: Jenkins Multi-Stage Pipeline

> The requested notes file, `9-Jenkins-Multi-Stage-Pipeline.md`, was not found in the workspace or tracked repository when this was prepared. This guide follows the supplied objective and requirements: a Python Flask application verified by a Jenkins pipeline with Build, Test, and Deploy stages, followed by a run and endpoint check.

## Objective and CI overview

This exercise demonstrates Continuous Integration with a small Flask application. Jenkins checks out the existing repository, prepares an isolated Python environment, installs the app dependency, runs automated tests, copies application files into a workspace-local mock deployment directory, starts the deployed app, and makes an HTTP request to verify it. Jenkins pipelines make those repeatable steps and their results visible as stages in the build.

The required stages remain named **Build**, **Test**, and **Deploy**. **Run Application** and **Test Application** are supporting stages that exercise and verify the mock deployment. This is a mock deployment within the Jenkins workspace, not a production deployment.

## Project files

```text
Ex 9/
├── .gitignore
├── Jenkinsfile
├── README.md
├── app.py
├── requirements.txt
└── test_app.py
```

- `app.py` defines the Flask app and returns the required greeting from `/`.
- `requirements.txt` declares Flask, the application's runtime dependency.
- `test_app.py` uses `unittest` and Flask's test client to verify status, exact body, and an unknown-route 404.
- `Jenkinsfile` defines the six-stage declarative flow (checkout, Build, Test, Deploy, Run Application, and Test Application), with local mock deployment, HTTP verification, and cleanup.

## Prerequisites

For local execution, use Python 3.10 or newer and pip. For the Jenkins pipeline, configure an agent with a POSIX/Linux shell, Python 3.10+, pip, Python `venv` support (including `ensurepip`), Git, and outbound package-index access to install Flask. `agent any` selects an available Jenkins agent; this Jenkinsfile checks for a Unix agent and fails clearly on Windows because the run/cleanup stages use POSIX shell commands. It does not assume the Jenkins controller or agent already has Flask.

No Docker image is required by this exercise. A Docker-based Jenkins controller does not automatically provide these tools to an agent; install Python and Git on the agent using your organization's approved image/provisioning process. The pipeline creates a build-specific `.venv-ci-${BUILD_NUMBER}` in the workspace instead of installing packages globally or using root.

For repeatable agent setup, use a dedicated versioned Linux agent image with Python 3.10+, Git, pip, and `venv`/`ensurepip` already provisioned. Configure that agent for this job using your Jenkins administration process. Do not alter a running Jenkins controller or install Python dependencies globally during a build.

## Run locally

From the repository root in Windows PowerShell:

```powershell
$project = (Resolve-Path '.\Ex 9').Path
$venv = Join-Path $project '.venv'
py -m venv $venv
& "$venv\Scripts\python.exe" -m pip install -r "$project\requirements.txt"
& "$venv\Scripts\python.exe" -m unittest discover -s $project -v
& "$venv\Scripts\python.exe" "$project\app.py"
```

Open <http://127.0.0.1:5000/>. The response must be exactly:

```text
Hello, Jenkins Multi-Stage Pipeline!
```

Stop the local server with Ctrl+C. To test the app at another local port, set `PORT` before starting it, for example `$env:PORT = '5050'` in PowerShell, then visit port 5050.

On Linux, run from the repository root:

```sh
python3 -m venv 'Ex 9/.venv'
'Ex 9/.venv/bin/python' -m pip install -r 'Ex 9/requirements.txt'
'Ex 9/.venv/bin/python' -m unittest discover -s 'Ex 9' -v
'Ex 9/.venv/bin/python' 'Ex 9/app.py'
```

## Jenkins installation and status

Before installing or starting Jenkins, inspect existing containers; do not remove or recreate an existing instance or its data:

```powershell
docker ps -a --filter "name=^/jenkins$"
```

If the intended container exists but is stopped, inspect it and start that same instance with `docker start jenkins`. If there is no existing instance, install Jenkins only after Docker Desktop is running Linux containers and ports 8080/50000 are available:

```powershell
docker run -d --name jenkins -p 8080:8080 -p 50000:50000 jenkins/jenkins:lts
docker ps -a
```

Open <http://localhost:8080/> and complete the setup wizard. Keep the generated initial administrator password private. If ports conflict, do not remove an existing container; inspect and choose an unused host port for a separate lab instance instead.

The supported pipeline agent must provide `python3 -m venv`. If that module is missing, the Build stage fails with a clear message; provision the agent's Python venv support through the approved agent image/configuration, rather than installing packages globally in the Jenkins controller.

```powershell
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

The initial administrator password is generated for the user's own Jenkins instance. Keep it private and never commit it. The interactive alternative is `docker exec -it jenkins bash`, followed by `cat /var/jenkins_home/secrets/initialAdminPassword` inside the container. The Jenkins container may not include Python; do not install system packages into a running Jenkins container as root for this lab. Use a suitably provisioned agent instead.

## Create the Pipeline job

The configured `origin` URL is `https://github.com/ANSHIKAAGRAWAL1/devops.git`. Use this existing repository; do not create another repository. The job must check out the repository root, where the script path is `Ex 9/Jenkinsfile`.

1. In the Jenkins web interface, choose **New Item**, enter a job name such as `Exercise 9 Flask Pipeline`, choose **Pipeline**, then select **OK**.
2. Under **Pipeline**, set **Definition** to **Pipeline script from SCM** and **SCM** to **Git**.
3. Enter `https://github.com/ANSHIKAAGRAWAL1/devops.git` as the **Repository URL** and set the branch specifier to `*/main` (or the branch that contains this exercise).
4. Set **Script Path** to exactly `Ex 9/Jenkinsfile`; leave lightweight checkout enabled if the Git plugin offers it.
5. Save and choose **Build Now**. Open the build page to inspect stage results and **Console Output**.

These job creation and SCM settings are manual web-interface steps; the files do not configure a job inside Jenkins automatically.

For a public repository, read-only checkout normally needs no credential. If the repository is private, add an SSH key or narrowly scoped access token in Jenkins **Manage Jenkins > Credentials**, then select its credential ID in the Git SCM settings. Do not embed credentials in this repository, a Jenkinsfile, or a repository URL.

## Pipeline behavior

1. **Checkout:** runs `checkout scm` to populate the configured repository workspace; automatic checkout is intentionally disabled to make this stage explicit.
2. **Build:** verifies `python3` and pip, creates `.venv-ci-${BUILD_NUMBER}` under `Ex 9`, and installs `requirements.txt`. Any command failure stops the build.
3. **Test:** runs `python3 -m unittest discover -s . -v` using the virtual environment, with verbose results in the console.
4. **Deploy:** copies `app.py` and `requirements.txt` to `${WORKSPACE}/python-app-deploy-${BUILD_NUMBER}` and checks both files exist. This directory stays within the Jenkins workspace.
5. **Run Application:** selects a free local port, starts the deployed Flask app as a tracked background process, and saves its PID and log in the deployment directory.
6. **Test Application:** waits up to 30 seconds for the endpoint, then checks HTTP 200 and the exact response body. The pipeline has a 10-minute overall timeout.

Declarative `post` actions report success/failure and always stop the tracked process and remove only the deployment directory and build-specific virtual environment created by this build. Do not overlap workspace cleanup with another job; concurrent builds of this pipeline are disabled.

## Troubleshooting

- **Python or pip missing:** install Python 3.10+ and pip on the selected agent, verify `python3` is on `PATH`, and confirm `python3 -m pip --version` works.
- **Virtual environment creation fails:** install/configure Python's `venv`/`ensurepip` support on the agent; do not work around it by installing Flask globally or as root.
- **Git checkout fails:** verify the SCM repository URL, branch, Git plugin, network access, and (for a private repository) selected Jenkins credential.
- **Flask install fails:** inspect the Build console output for package-index/network errors and confirm the agent can reach its configured package index.
- **Tests fail:** inspect the Test stage's verbose `unittest` output and reproduce locally with `python -m unittest discover -s 'Ex 9' -v` from the repository root.
- **App port or startup issue:** the pipeline chooses a currently free loopback port. Check the Run Application log printed by a failed health check and make sure the agent permits local loopback connections.
- **Deploy file missing:** verify the checkout is the repository root and the job's script path is `Ex 9/Jenkinsfile`; the Deploy stage expects source files in `Ex 9`.
- **Windows agent selected:** this Jenkinsfile intentionally requires a Unix agent for POSIX process control. Label/configure an appropriate Linux agent; `agent any` does not guarantee the selected node is Linux.
- **Jenkins container running but job lacks Python:** use a Python-capable agent. Do not mutate or recreate the existing Jenkins container or grant it extra privileges for this assignment.

## Cleanup

The pipeline removes only its per-build workspace deployment folder and virtual environment. It does not create, stop, or delete Jenkins containers. Stop Jenkins only if you intentionally started a dedicated lab instance and no one else uses it; keep existing/shared Jenkins data. Do not remove shared containers, volumes, or arbitrary workspace directories as cleanup.

## Current verification status

The Flask tests and local app can be verified separately from Jenkins. Jenkins job configuration and pipeline execution require manual setup in the Jenkins web interface and a suitable Linux agent. No Jenkins build result is claimed by this repository change.
