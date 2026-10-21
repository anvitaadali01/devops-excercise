# Exercise 1: Kubernetes Getting Started - Hello Pod

## Objective and scenario

This lab deploys Nginx as a Kubernetes Pod, exposes it with a NodePort Service, and opens the Nginx welcome page. Think of a Zepto storefront: the web frontend must run in a container and be reachable through a stable Kubernetes Service instead of depending on a Pod's changing address.

## Kubernetes, Pods, and Services

Kubernetes orchestrates containerized workloads across a cluster. A Pod is the smallest schedulable Kubernetes unit and contains one or more related containers. A Service provides a stable network endpoint and selects matching Pods by labels. This lab uses a `NodePort` Service to expose the Nginx Pod through a port on the Minikube node.

## Prerequisites and installation

Install a supported container driver (Docker Desktop is convenient on Windows/macOS), Minikube, and kubectl. Verify the tools before creating a cluster:

```powershell
docker version
minikube version
kubectl version --client
```

Installation guidance:

- **Windows:** install Docker Desktop with its Linux-container engine enabled. Install Minikube and kubectl from their official Windows instructions, or use Chocolatey with `choco install minikube kubernetes-cli`. Run PowerShell as your regular user with Docker Desktop available.
- **Linux:** install Docker or another Minikube-supported driver, then install Minikube and kubectl using the official instructions for your distribution. Ensure your user can access the chosen driver without using root for routine cluster commands.
- **macOS:** install Docker Desktop or another supported driver; with Homebrew, install the clients using `brew install minikube kubectl`.
- **WSL:** install a Linux distribution with WSL 2, then follow its Linux Minikube/kubectl instructions. If using Docker Desktop, enable WSL integration for that distribution and verify `docker version` works inside WSL. Do not start competing Minikube clusters from Windows and WSL without choosing which environment owns the cluster.

Official references: [Minikube start guide](https://minikube.sigs.k8s.io/docs/start/), [kubectl installation](https://kubernetes.io/docs/tasks/tools/), and [Docker Desktop](https://docs.docker.com/desktop/).

## Start Minikube

Inspect existing profiles and resources before starting or changing a cluster. If you already use Minikube, do not reset or delete it for this lab.

```sh
minikube profile list
minikube start
kubectl get nodes
```

## Deploy Nginx

Choose **one** creation approach below. They create resources with the same names; running both does not create a second independent Pod or Service and can result in `AlreadyExists` or configuration conflicts.

### Option A: imperative commands

```sh
kubectl run hello-k8s --image=nginx --port=80
kubectl get pods
kubectl describe pod hello-k8s
kubectl expose pod hello-k8s --type=NodePort --port=80
kubectl get services
```

### Option B: YAML manifests

From the repository root, apply the two files in order:

```sh
kubectl apply -f "Ex 1/hello-k8s.yaml"
kubectl apply -f "Ex 1/hello-k8s-service.yaml"
kubectl get pods
kubectl get services
kubectl describe pod hello-k8s
```

The Pod has label `app: hello-k8s`, and the Service selects that same label. Wait for the Pod to show `Running` and `1/1` Ready before opening the Service:

```sh
kubectl get pods -w
```

Stop watching with Ctrl+C; this does not stop the Pod.

## Open the Nginx welcome page

```sh
minikube service hello-k8s
```

Minikube may open a browser or print a URL. Use the URL returned by your machine rather than assuming a fixed NodePort or localhost port. The command may keep a tunnel process attached to its terminal; leave that terminal open while browsing. The page should display the default **Welcome to nginx!** page.

## Troubleshooting

- **Pod is `Pending`:** inspect `kubectl describe pod hello-k8s` and `kubectl get events --sort-by=.lastTimestamp`. Confirm the Minikube node is Ready and has enough resources.
- **Image pull fails or shows `ImagePullBackOff`:** inspect Pod events and check that the node can reach the image registry. Nginx is pulled from the public `nginx` image; verify Docker/Minikube networking and try `minikube status` before changing resources.
- **Pod is not Ready:** inspect `kubectl logs hello-k8s` and `kubectl describe pod hello-k8s`; wait for the image download and container startup.
- **Service has no endpoints:** check `kubectl get pods --show-labels` and `kubectl describe service hello-k8s`. The selector must match the Pod's `app: hello-k8s` label and the Pod must be Ready.
- **Service URL is inaccessible:** run `minikube service hello-k8s` again and use the actual URL. Keep its terminal open if it provides a tunnel, confirm the Pod and Service are in the same current namespace, and check host firewall/VPN settings.
- **`AlreadyExists` after changing approaches:** inspect the existing Pod and Service first. Delete only the lab resources you intend to replace, then apply the chosen method; do not create duplicates or delete unrelated resources.

## Inspect and clean up safely

Inspect the resources before cleanup:

```sh
kubectl get pods,services
kubectl describe pod hello-k8s
kubectl describe service hello-k8s
```

Remove only this lab's Service and Pod (manifest-based commands shown):

```sh
kubectl delete -f "Ex 1/hello-k8s-service.yaml" --ignore-not-found
kubectl delete -f "Ex 1/hello-k8s.yaml" --ignore-not-found
```

For resources created imperatively, the equivalent targeted cleanup is:

```sh
kubectl delete service hello-k8s --ignore-not-found
kubectl delete pod hello-k8s --ignore-not-found
```

Do not use broad commands such as `kubectl delete all --all`. `minikube stop` stops the entire Minikube profile and affects every workload in it; use it only if you own the profile and have checked for other work. `minikube delete` destroys the profile's cluster state. Do not run it unless you have explicitly confirmed that the profile and all its data may be discarded. This guide does not stop or delete clusters automatically.

## Submission screenshot checklist

- Minikube status or `kubectl get nodes` showing the cluster node Ready.
- `kubectl get pods` showing `hello-k8s` Running and Ready.
- `kubectl get services` or `kubectl describe service hello-k8s` showing the NodePort Service.
- The Nginx welcome page opened at the actual URL returned by Minikube.

Capture screenshots from your own run. No Pod status, URL, or browser result is claimed by this repository change.
