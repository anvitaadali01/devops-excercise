# Exercise 10: Minikube Multi-Node, Multi-App Deployment

> The requested notes file, `10-Minikube-Multi-Node-Multi-App-Minikube-Deployment.md`, was not present in the workspace or tracked repository when this was prepared. This guide follows the assignment requirements supplied in the request.

## Objective and architecture

Deploy two Flask applications to a three-node Minikube profile. Product Catalog serves three products and runs two replicas; Shopping Cart serves an in-memory cart and runs three replicas. Required pod anti-affinity on `kubernetes.io/hostname` prevents replicas of the same app from sharing a node, so the two catalog pods must use separate nodes and the three cart pods need three eligible nodes. Both Services are `NodePort` resources in the `default` namespace.

The containers listen on port 80. Images are built locally, loaded into the `devops-multinode` Minikube profile, and used with `imagePullPolicy: Never`. No registry-push flow is mixed into this local image-load workflow.

## Files

```text
Ex 10/
├── Dockerfile.product
├── Dockerfile.shopping
├── README.md
├── product_catalog.py
├── product_catalog_deployment.yaml
├── product_catalog_service.yaml
├── requirements.txt
├── shopping_cart.py
├── shopping_cart_deployment.yaml
└── shopping_cart_service.yaml
```

- `product_catalog.py`: Flask `GET /products` endpoint with the assignment's product data.
- `shopping_cart.py`: Flask `GET /cart` and validated `POST /cart` endpoints; cart state is in memory and resets when the pod restarts.
- `requirements.txt`: pinned Flask dependency shared by both apps.
- `Dockerfile.product` and `Dockerfile.shopping`: build the two separate images and expose container port 80.
- The two `*_deployment.yaml` files define 2 and 3 replicas with required hostname pod anti-affinity and local-image pull policy.
- The two `*_service.yaml` files define matching `default`-namespace NodePort Services.

## Prerequisites

Use Docker Desktop with its Docker engine running, Minikube, kubectl, and Python 3.10+ with pip for local tests. Check the tools without changing any cluster:

```powershell
docker version
docker info
minikube version
kubectl version --client
minikube profile list
```

Before creating the requested profile, inspect it specifically:

```powershell
minikube -p devops-multinode status
```

If that profile already exists, inspect its nodes and workloads before proceeding; do not delete or reset it automatically. The `minikube` profile is separate from `devops-multinode`.

## Create the three-node cluster

Only when Docker is running and you have confirmed there is no existing `devops-multinode` state to preserve, create the profile:

```powershell
minikube start --nodes 3 -p devops-multinode
kubectl --context devops-multinode get nodes -o wide
```

The Docker driver should normally run as the regular user that owns Docker Desktop, not as root. Do not add `--force` as a routine workaround. The notes mention it for root execution; instead, correct Docker permissions or use the supported non-root Docker Desktop setup. This cluster-creation command was not run while preparing this repository change.

## Build and load the images

From the repository root in PowerShell, enter `Ex 10` and build both images from that directory:

```powershell
Push-Location '.\Ex 10'
docker build -t product-catalog:latest -f Dockerfile.product .
docker build -t shopping-cart:latest -f Dockerfile.shopping .
Pop-Location
```

Make both local images available to the chosen Minikube profile using **image load**:

```powershell
minikube -p devops-multinode image load product-catalog:latest
minikube -p devops-multinode image load shopping-cart:latest
minikube -p devops-multinode image ls
```

The Deployments set `imagePullPolicy: Never`, so Kubernetes must find each image locally on the node selected for a pod. Verify image availability for every Minikube node using `minikube -p devops-multinode node list` and, if a pod reports `ErrImageNeverPull`, inspect that node's runtime image list with the Minikube node SSH/CRI tools and reload the image into the profile. Do not switch to a registry push unless you also change image references and document that separate method. The registry add-on is not needed for this image-load workflow.

## Apply the Kubernetes resources

From the repository root:

```powershell
kubectl --context devops-multinode apply -f ".\Ex 10\product_catalog_deployment.yaml"
kubectl --context devops-multinode apply -f ".\Ex 10\shopping_cart_deployment.yaml"
kubectl --context devops-multinode apply -f ".\Ex 10\product_catalog_service.yaml"
kubectl --context devops-multinode apply -f ".\Ex 10\shopping_cart_service.yaml"
```

Verify nodes, deployments, services, and pod placement:

```powershell
kubectl --context devops-multinode get nodes
kubectl --context devops-multinode get deployments
kubectl --context devops-multinode get services
kubectl --context devops-multinode get pods -o wide
kubectl --context devops-multinode rollout status deployment/product-catalog
kubectl --context devops-multinode rollout status deployment/shopping-cart
```

Expected: five application pods total, all `Running` and `Ready`; two `product-catalog` pods on different nodes and three `shopping-cart` pods distributed one per node. These are expectations, not deployment results. Required anti-affinity and cluster capacity determine whether scheduling succeeds. If fewer than three eligible nodes are Ready, the cart Deployment will leave pods Pending by design.

## Access and test the Services

Run each command and keep its terminal open if Minikube creates a service tunnel. Minikube may open a browser or print a URL:

```powershell
minikube -p devops-multinode service product-catalog-service
minikube -p devops-multinode service shopping-cart-service
```

Copy the actual URLs printed by your environment. Do not assume sample localhost ports are fixed. Substitute them for `<PRODUCT_CATALOG_URL>` and `<SHOPPING_CART_URL>` below (remove the angle brackets):

```sh
curl http://<PRODUCT_CATALOG_URL>/products
curl http://<SHOPPING_CART_URL>/cart
```

The Product Catalog response should be:

```json
[
  {"id": 1, "name": "Laptop", "price": 1200},
  {"id": 2, "name": "Phone", "price": 800},
  {"id": 3, "name": "Headphones", "price": 150}
]
```

The initial Shopping Cart response should be `[]`. Add the example item:

```sh
curl -X POST http://<SHOPPING_CART_URL>/cart \
  -H "Content-Type: application/json" \
  -d '{"id": 1, "name": "Laptop", "quantity": 1}'
```

The POST should return HTTP 201 with `[ {"id": 1, "name": "Laptop", "quantity": 1} ]` (without the illustrative spacing), and a subsequent GET `/cart` to that same pod should return the same list. Because the cart is in memory and Kubernetes may route requests to another replica, a later Service GET can reach a different pod and show an empty cart; state is neither shared between replicas nor persistent across restarts.

For a deterministic same-pod GET/POST/GET demonstration, list the cart pods and port-forward directly to one actual pod in another terminal:

```powershell
kubectl --context devops-multinode get pods -l app=shopping-cart -o wide
kubectl --context devops-multinode port-forward pod/ACTUAL_SHOPPING_CART_POD 8081:80
```

Keep the port-forward terminal open and use `http://127.0.0.1:8081` as `SHOPPING_CART_URL` for the initial GET, POST, and follow-up GET. Replace `ACTUAL_SHOPPING_CART_POD` with a pod name returned by the first command. This pins the test to one pod without changing the app's intentionally in-memory storage.

## Troubleshooting

- **Docker or Minikube cannot start:** check `docker info` and `minikube profile list`; start Docker Desktop, but do not reset/delete an existing profile without confirming its contents are disposable.
- **`ImagePullBackOff` or `ErrImageNeverPull`:** verify exact image tags with `docker images` and profile/node image availability with `minikube -p devops-multinode image ls`. Rebuild and image-load both images; `Never` will not pull from a registry.
- **Pods remain `Pending`:** inspect `kubectl --context devops-multinode describe pod <POD_NAME>` and node readiness/capacity. Required anti-affinity needs one distinct eligible node per replica of the same app.
- **Anti-affinity appears unsatisfied:** ensure three nodes are Ready for all three cart replicas and that labels/selectors match. The rules are required, not best-effort.
- **Wrong namespace or no Service endpoints:** these manifests consistently use `default`; check `kubectl --context devops-multinode get pods,services -n default -o wide` and confirm Service selectors match pod labels.
- **NodePort is inaccessible:** use `minikube -p devops-multinode service <SERVICE_NAME>` and the URL actually returned. Keep its terminal open if it owns a tunnel; ensure all pods are Ready and check the host firewall/VPN if needed.
- **Cart differs between requests:** the list is in-memory per pod; requests can be routed to different replicas. This is expected for this exercise and is not durable storage.
- **POST returns 400:** send a JSON object containing a positive integer `id`, a non-empty string `name`, and a positive integer `quantity`.

## Cleanup and data safety

To remove only the four Exercise 10 Kubernetes resources after confirming they were created by this exercise, run from the repository root:

```powershell
kubectl --context devops-multinode delete -f ".\Ex 10\shopping_cart_service.yaml"
kubectl --context devops-multinode delete -f ".\Ex 10\product_catalog_service.yaml"
kubectl --context devops-multinode delete -f ".\Ex 10\shopping_cart_deployment.yaml"
kubectl --context devops-multinode delete -f ".\Ex 10\product_catalog_deployment.yaml"
```

The notes also mention `minikube stop` and `minikube delete`. **Stop** shuts down all nodes in that profile and interrupts its workloads. **Delete** destroys the profile and its cluster state. Run neither against an existing/shared profile without checking ownership and receiving explicit confirmation that the affected state may be stopped or permanently discarded. No stop/delete commands are run automatically by this guide.

## Submission screenshots

Capture your own evidence after a real deployment:

1. `kubectl get nodes` showing the three profile nodes Ready.
2. Deployments and Services showing 2/3 replicas and the NodePort Services.
3. `kubectl get pods -o wide` showing all five Ready pods and their actual node assignments.
4. Product Catalog `/products` JSON response.
5. Shopping Cart initial GET response, successful POST status/body, and a subsequent GET response.

Do not invent node assignments, URLs, pod names, or successful outputs. No cluster deployment or screenshots are claimed by this repository change.
