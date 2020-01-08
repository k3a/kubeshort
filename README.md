# KubeShort

Shortcuts to the most common kubectl actions.

## Examples

* `k.use kube-system`: switch the current working namespace to the `kube-system` 
* `k.po` - list pods in the current namespace
* `k.po -n default` - list pods, overwriting namespace temporarily for the command
* `k.scale mydeployment=2`: scale deployment, replicaset, statefulset or replicationcontroller to 2 replicas
* `k.logs pods/my-pod-name -f`: return 20 most recent logs of all containers in a pod and follow the streams
* `k.no.top`: current near-realtime CPU and RAM usage of nodes in mCPU and memory units (current cpu/mem usage)
* `k.no.res`: resources allocated (requests and limites) by workloads for each node (node utilization)
* `k.no.drain -C`: completely drain node (ignoring pods with emptyDir, daemonsets and stray pods: --force --delete-local-data --ignore-daemonsets)
* `k.ctx other-cluster`: switch to other-cluster context (instead of kubectl use-context)
* `k.ctx`: see the current context
* `k get pods`: just like `kubectl get pods`, with `-n current-namespace` is auto-appended

See the source code or `./_ks.py -h` output for more shortcuts.

## Contributions

This tool was made to help me save time writing long, repetitive kubectl commands.
It shouldn't be considered fully-featured `kubectl` replacement, following official design documentations or implementing every possible resource and CRD.
The purpose is simply to make life easier by simplifying most-commonly made actions on common resources.

That said, I am open for contributions and suggestions.
Python is not my primary language so I am probably also not following its best practices. :P

## License

GNU GPL v3
