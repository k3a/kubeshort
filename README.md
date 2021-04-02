# KubeShort

Shortcuts to the most common kubectl actions.

## Examples

* `k.use kube-system`: switch the current working namespace to the `kube-system` 
* `k.po` - list pods in the current namespace
* `k.po -n default` - list pods, overwriting namespace temporarily for the command
* `k.po.del pod-name` - delete pod pod-name
* `k.po.y pod-name` - show filtered, less cluttered [kubectl-neat-like](https://github.com/itaysk/kubectl-neat) yaml representation (or original yaml with -f/--full option) 
* `k.po.x pod-name uptime` - execute "uptime" command in the container, returning stdout or attach to a shell if no command is specified
* `k.scale mydeployment=2`: scale deployment, replicaset, statefulset or replicationcontroller to 2 replicas
* `k.logs pods/my-pod-name -f`: return 20 most recent logs of all containers in a pod and follow the streams ("pods/" prefix optional)
* `k.sec.y secret-name`: return YAML representation of secret named secret-name
* `k.no.top`: current near-realtime CPU and RAM usage of nodes in mCPU and memory units (current cpu/mem usage)
* `k.no.res`: resources allocated (requests and limites) by workloads for each node (node utilization)
* `k.no.x node-name`: SSH into the node using public node IP and `KUBESHORT_DEFAULT_USER` user
* `k.no.dr -C my-node-name`: completely drain node (ignoring pods with emptyDir, daemonsets and stray pods: --force --delete-local-data --ignore-daemonsets)
* `k.ctx other-cluster`: switch to other-cluster context (instead of kubectl use-context)
* `k.ctx`: see the current context
* `k.apl.f file.yaml`: kubectl apply -f file.yaml
* `k get pods`: just like `kubectl get pods`, with `-n current-namespace` is auto-appended

See the source code or `./_ks.py -h` output for more shortcuts.

## Install
```sh
# use your custom bin directory (optional)
mkdir ~/bin
export PATH="$HOME/bin/:$PATH"

# move to your bin directory
chmod +x ./_ks.py
cp ./_ks.py ~/bin/

# let it create symlinks to itself in your bin directory
_ks.py install-symlinks -t ~/bin/
```

## Configuration

You can customize these environmental variables:

- `KUBESHORT_CUR_NS_PATH`: path to store the current, working namespace name (default /tmp/.k8s-cur-ns)
- `KUBESHORT_ALLOW_SHORT`: whether to create also shorter versions of common resources (e.g. "cj" for "cronjob", default "1")
- `KUBESHORT_DEFAULT_TAIL`: number of log lines to return (default 20)
- `KUBESHORT_DEFAULT_USER`: default user when SSH'ing into a node (default ubuntu)

## Extras

### k.logcli

A wrapper around [logcli](https://grafana.com/docs/loki/latest/getting-started/logcli/) to automatically create and teardown port-forwarding and fetch common log labels.

## Contributions

This tool was made to help me save time writing long, repetitive kubectl commands.
It shouldn't be considered fully-featured `kubectl` replacement, following official design documentations or implementing every possible resource and CRD.
The purpose is simply to make life easier by simplifying most-commonly made actions on common resources.

That said, I am open for contributions and suggestions.
Python is not my primary language so I am probably also not following its best practices. :P

## License

GNU GPL v3
