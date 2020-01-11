#!/usr/bin/python

# KubeShort - shortcuts to the most common kubectl actions
#
# Shortcuts by default starts with "k."" prefix and are symlinked to this script.
#
# To create symlinks, run:
# $ /path/to/_ks.py install-symlinks -t /target/directory/for/symlinks/
#
# Created symlinks will point to the _ks.py using relative paths.
# Add /target/directory/for/symlinks to your PATH:
# $ export PATH="/target/directory/for/symlinks:${PATH}"
#
# Copyright 2020 Mario Hros (K3A.me)
# License: GNU GPL v3

import sys
import os
import uuid
import argparse
import subprocess
import re
import json
import shutil
from pipes import quote

# script name (to which symlinks should point to)
SCRIPT_FILE_NAME = "_ks.py"
# where to store the current namespace
CUR_NS_PATH = "/tmp/.k8s-cur-ns"
# prefix for all helpers (and thus also for the creaed symlinks)
HELPER_PREFIX = "k."
# allow even shorter object names (e.g. "cj" for "cronjob") which are not officialy accepted by kubectl get <shortname>
ALLOW_SHORT = True
# default number of log lines to return (must be string variable)
DEFAULT_TAIL = "20"
# known k8s resources (to strip "resource/"NAME prefix)
KNOWN_K8S_RESOURCES = ["bindings", "componentstatuses", "configmaps", "endpoints", "events", "limitranges", "namespaces", "nodes", "persistentvolumeclaims",
                       "persistentvolumes", "pods", "podtemplates", "replicationcontrollers", "resourcequotas", "secrets", "serviceaccounts", "services",
                       "mutatingwebhookconfigurations", "validatingwebhookconfigurations", "customresourcedefinitions", "apiservices", "controllerrevisions",
                       "daemonsets", "deployments", "replicasets", "statefulsets", "meshpolicies", "policies", "tokenreviews", "localsubjectaccessreviews",
                       "selfsubjectaccessreviews", "selfsubjectrulesreviews", "subjectaccessreviews", "horizontalpodautoscalers", "verticalpodautoscalercheckpoints",
                       "verticalpodautoscalers", "cronjobs", "jobs", "certificatesigningrequests", "certificates", "challenges", "clusterissuers", "issuers",
                       "orders", "backendconfigs", "adapters", "attributemanifests", "handlers", "httpapispecbindings", "httpapispecs", "instances",
                       "quotaspecbindings", "quotaspecs", "rules", "templates", "leases", "daemonsets", "deployments", "ingresses", "networkpolicies",
                       "podsecuritypolicies", "replicasets", "capacityrequests", "nodes", "pods", "managedcertificates", "destinationrules", "envoyfilters",
                       "gateways", "serviceentries", "sidecars", "syntheticserviceentries", "virtualservices", "ingresses", "networkpolicies",
                       "runtimeclasses", "updateinfos", "poddisruptionbudgets", "podsecuritypolicies", "clusterrolebindings", "clusterroles", "rolebindings",
                       "roles", "clusterrbacconfigs", "rbacconfigs", "servicerolebindings", "serviceroles", "scalingpolicies", "priorityclasses", "authorizationpolicies",
                       "csidrivers", "csinodes", "storageclasses", "volumeattachments",

                       "cs", "cm", "ep", "ev", "limits", "ns", "no", "pvc", "pv", "po", "rc", "quota", "sa", "svc", "crd", "crds", "apps", "ds", "deploy", "rs", "sts",
                       "hpa", "vpacheckpoint", "vpa", "cj", "batch", "csr", "cert", "certs", "ds", "deploy", "ing", "netpol", "psp", "rs", "capreq", "mcrt", "dr",
                       "gw", "se",  "vs", "ing", "netpol", "updinf", "pdb", "psp", "pc", "sc"
                       ]

# fail with an error message
def fail(msg):
    print(msg, file=sys.stderr)
    sys.exit(-1)

# random 5-character identifier
def rand_ident():
    return str(uuid.uuid4().fields[-1])[:5]

# Returns length of the longest value of attrname key-name in the subkeys of obj.
# Example:
# obj:
#  - subkey1:
#    attrname: "some str"
#  - subkey2:
#    attrname: "other str"
def max_attr_len(obj, subkeys, attrname):
    nlen = 0
    for sub in subkeys:
        if sub in obj:
            for sobj in obj[sub]:
                l = len(sobj[attrname])
                if l > nlen:
                    nlen = l
    return nlen

# exec kubectl, replacing the current process
def exec_kubectl(args, pager=False):
    pager_tool = None

    if pager and sys.stdout.isatty():
        pager_tool = shutil.which("less")
        if not pager_tool:
            pager_tool = shutil.which("more")

    if pager_tool:
        args = ["kubectl"] + args
        os.execvp("sh", ["sh", "-c", ' '.join(quote(arg)
                                              for arg in args)+"|"+pager_tool])
    else:
        os.execvp("kubectl", ["kubectl"] + args)

# run kubectl and return stdout
def run_kubectl(args):
    res = subprocess.run(['kubectl'] + args, stdout=subprocess.PIPE)
    return str(res.stdout, encoding="utf-8")

# run kubectl and return json-decoded array of items
def kubectl_items(args):
    j = json.loads(run_kubectl(args))

    items = []
    if "items" in j:
        items = j["items"]
    else:
        items = [j]

    return items


cur_ns = ""

# get currently-selected namespace
def get_ns():
    global cur_ns

    if len(cur_ns) > 0:
        return cur_ns

    if os.path.exists(CUR_NS_PATH):
        with open(CUR_NS_PATH, "rb") as f:
            cur_ns = str(f.read(), encoding="utf-8")
            f.close()
            return cur_ns
    else:
        return "default"

# set the current namespace
def set_ns(ns: str):
    global cur_ns

    with open(CUR_NS_PATH, "wb") as f:
        f.write(ns.encode("utf-8"))
        cur_ns = ns
        f.close()


# list of known helper names (the name after "k.") which will be created
# as symbolic links and assigned argument-mediating functions
symlink_helpers = {}

# the name of the current helper (if run through a symlink)
this_helper = os.path.basename(sys.argv[0])
if this_helper.startswith(HELPER_PREFIX):
    this_helper = this_helper[len(HELPER_PREFIX):]


def safe_symlink(src, dst):
    print("symlink", dst, "->", src)

    try:
        os.remove(dst)
    except:
        pass
    os.symlink(src, dst)


def make_symlinks(args):
    this_script_dir = os.path.dirname(sys.argv[0])
    tgt = this_script_dir
    if args.target_path != None:
        tgt = args.target_path

    rel_path = os.path.relpath(this_script_dir, tgt)
    rel_script_target = os.path.join(rel_path, SCRIPT_FILE_NAME)

    # basic symlink
    symlink_path = os.path.join(tgt, "k")
    safe_symlink(rel_script_target, symlink_path)

    # helper symlinks
    for h in symlink_helpers:
        symlink_path = os.path.join(tgt, HELPER_PREFIX + h)
        safe_symlink(rel_script_target, symlink_path)

    print("Created symbolic links at %s" % tgt)
    sys.exit()


parser = argparse.ArgumentParser()
subparser = parser.add_subparsers()


def shared_help(help_func, base_form):
    def h():
        help_func()
        print()

        if base_form != None:
            exec_kubectl(base_form + ["--help"])
    return h


def apply_ns(args, p=None):
    if p != None and hasattr(p, "namespace"):
        args.append("-n")
        args.append(p.namespace if len(p.namespace) > 0 else get_ns())
    else:
        has_ns = False
        for a in args:
            if a == "-n" or a == "--namespace":
                has_ns = True
                break
        if not has_ns:
            args += ["-n", get_ns()]

    return args


def strip_resource_prefix(n):
    nparts = n.split("/")
    if len(nparts) == 2 and (nparts[0].lower() in KNOWN_K8S_RESOURCES or nparts[0].lower()+"s" in KNOWN_K8S_RESOURCES):
        return os.path.basename(nparts[1])
    else:
        return n


def default_func_middleware(base_form):
    def f(p, extra_args):
        args = []
        for a in extra_args:
            if a.startswith("-"):
                args.append(a)
            else:
                args.append(strip_resource_prefix(a))

        args = apply_ns(args, p)
        exec_kubectl(base_form + args)
    return f


def register_helper(name, description, base_form=None, namespaced=True, func=None):
    if base_form == None and func == None:
        fail("base_form or func argument must be defined for register_helper()")

    if name not in symlink_helpers:
        symlink_helpers[name] = []

    p = argparse.ArgumentParser(name, description=description)
    p.print_help = shared_help(p.print_help, base_form)
    if func != None:
        p.set_defaults(func=func)
    else:
        p.set_defaults(func=default_func_middleware(base_form))

    if namespaced:
        p.add_argument("-n", "--namespace",
                       help="Namespace to work with", default=get_ns())

    symlink_helpers[name].append(p)

    return p


def register_common_helpers(name, k8s_obj_name, long_name=None, namespaced=True):
    if long_name == None:
        long_name = k8s_obj_name

    register_helper(name, "get "+long_name,
                    ["get", k8s_obj_name], namespaced=namespaced)
    register_helper(name+".w", "get "+long_name+" (wide)",
                    ["get", k8s_obj_name, "-o", "wide"], namespaced=namespaced)
    register_helper(name+".desc", "describe "+long_name,
                    ["describe", k8s_obj_name], namespaced=namespaced)
    register_helper(name+".del", "delete "+long_name,
                    ["delete", k8s_obj_name], namespaced=namespaced)
    register_helper(name+".ed", "edit "+long_name,
                    ["edit", k8s_obj_name], namespaced=namespaced)
    register_helper(name+".yaml", "get YAML representation of "+long_name,
                    ["get", k8s_obj_name, "-o", "yaml"], namespaced=namespaced)
    register_helper(name+".json", "get JSON representation of "+long_name,
                    ["get", k8s_obj_name, "-o", "json"], namespaced=namespaced)


def hlp_no_res(p, extra_args):
    out = run_kubectl(["describe", "node"] + extra_args)
    pattern = re.compile(
        r'(^Name:\s*(.*?)\n)|(^(Allocated resources:.*?)Events)', flags=re.MULTILINE | re.DOTALL)

    for (_, name, _, res) in re.findall(pattern, out):
        if len(name) > 0:
            name = "Name: " + name
        print(name, res)


def hlp_no_po(p, extra_args):
    out = run_kubectl(["describe", "node"] + extra_args)
    pattern = re.compile(
        r'(^Name:\s*(.*?)\n)|(^(Non-terminated Pods:.*?)Allocated)', flags=re.MULTILINE | re.DOTALL)

    for (_, name, _, res) in re.findall(pattern, out):
        if len(name) > 0:
            name = "Name: " + name
        print(name, res)


def hlp_use(p, extra_args):
    if p.set_ns != None:
        set_ns(p.set_ns)
        print("Switched to %s namespace." % p.set_ns, file=sys.stderr)
    else:
        print("Current namespace:", get_ns(), file=sys.stderr)


def hlp_ctx(p, extra_args):
    if p.set_ctx != None:
        exec_kubectl(["config", "use-context", p.set_ctx])
    else:
        exec_kubectl(["config", "get-contexts"])


def hlp_apply_f(p, extra_args):
    exec_kubectl(["apply", "-f", p.file_or_url] + extra_args)


def hlp_del_f(p, extra_args):
    exec_kubectl(["delete", "-f", p.file_or_url] + extra_args)


def hlp_apply_k(p, extra_args):
    exec_kubectl(["apply", "-k", p.file_or_url] + extra_args)


def get_node_external_host(node):
    exhost = None

    for addr in node["status"]["addresses"]:
        if exhost == None and addr["type"] == "ExternalDNS":
            exhost = addr["address"]
        elif addr["type"] == "ExternalIP":
            exhost = addr["address"]

    return exhost

# returns dict of node_name => externalIP keys
def get_nodes_with_external_host(get_node_args=[]):
    nodes = kubectl_items(["get", "node", "-o", "json"] + get_node_args)

    out = {}

    for node in nodes:
        exhost = get_node_external_host(node)
        out[node["metadata"]["name"]] = exhost

    return out


def hlp_no_x(p, extra_args):
    node_args = []
    if p.selector != None:
        node_args += ["-l", p.selector]
    if p.nodes != None:
        node_args += p.nodes

    nodes = get_nodes_with_external_host(node_args)

    for node_name in nodes:
        print("Name:", node_name, file=sys.stderr)

        node_host = nodes[node_name]
        if node_host == None:
            print("(no external access)", file=sys.stderr)
            continue

        cmd = []
        if p.sudo:
            cmd = ["sudo"]

        cmd += [p.command]

        subprocess.run(["ssh", "-o", "UserKnownHostsFile=/dev/null", "-o", "StrictHostKeyChecking=off",
                        p.user+"@"+node_host] + cmd)


def hlp_no_df(p, extra_args):
    node_args = []
    if p.selector != None:
        node_args += ["-l", p.selector]
    if p.nodes != None:
        node_args += p.nodes

    nodes = get_nodes_with_external_host(node_args)

    for node_name in nodes:
        print("Name:", node_name)

        node_host = nodes[node_name]
        if node_host == None:
            print("(no external access)", file=sys.stderr)
            continue

        cmd = []
        if p.sudo:
            cmd = ["sudo"]

        cmd += ["df", "-h"]

        res = subprocess.run(["ssh", "-o", "UserKnownHostsFile=/dev/null", "-o", "StrictHostKeyChecking=off",
                              p.user+"@"+node_host] + cmd, stderr=subprocess.DEVNULL, stdout=subprocess.PIPE)

        for l in str(res.stdout, encoding="utf-8").splitlines():
            if l.startswith("/"):
                print(l)


def hlp_no_drain(p, extra_args):
    args = extra_args
    if p.complete:
        args += ["--force", "--delete-local-data", "--ignore-daemonsets"]

    exec_kubectl(["drain"] + args)


def hlp_logs(p, extra_args):
    args = apply_ns(["logs"], p)
    positionals = []
    container_specified = False
    can_use_pager = True

    if p.selector != None:
        args += ["--selector", p.selector]
    if p.tail != None:
        args += ["--tail", p.tail]
    if p.container != None:
        args += ["--container", p.container]
        container_specified = True
    if p.follow:
        args += ["--follow"]
        can_use_pager = False
        # when follow is requested without --tail, return DEFAULT_TAIL most recent by default
        # to prevent flooding the console with complete log
        if p.tail == None:
            args += ["--tail", DEFAULT_TAIL]
    if p.previous:
        args += ["--previous"]
    if p.raw:
        can_use_pager = False

    for a in extra_args:
        if not a.startswith("-"):
            positionals += [a]
        else:
            args += [a]

    # container as the second positional
    if len(positionals) == 2:
        args += ["--container", positionals[1]]
        container_specified = True
        positionals = positionals[:1]

    if len(positionals) > 0:
        # fix pod/name to just name
        positionals[0] = strip_resource_prefix(positionals[0])

        # all containers by default
        if not container_specified and p.container is None:
            args += ["--all-containers"]

    args += positionals

    exec_kubectl(args, pager=can_use_pager)


def hlp_run(p, extra_args):
    args = apply_ns([], p)

    if p.name:
        args += [p.name]
    else:
        args += ["kube-short-"+rand_ident()]

    if p.image:
        args += ["--image", p.image]
    if p.generator:
        args += ["--generator", p.generator]
    if not p.no_rm:
        args += ["--rm"]
    if not p.no_it:
        args += ["-i", "-t"]

    exec_kubectl(["run"] + args + extra_args)


def hlp_po_x(p, extra_args):
    args = apply_ns([], p)

    if p.container:
        args += ["-c", p.container]

    if not p.no_it:
        args += ["-i", "-t"]

    num_positionals = 0
    for a in extra_args:
        if not a.startswith("-"):
            num_positionals += 1

    if num_positionals == 1:
        exec_kubectl(["exec"] + args + extra_args + ["bash"])
    else:
        exec_kubectl(["exec"] + args + extra_args)


def hlp_po_co(p, extra_args):
    args = apply_ns([], p)

    items = kubectl_items(["get", "pods", "-o", "json"] + args + extra_args)
    for pod in items:
        print("Name:", pod["metadata"]["name"])

        spec = pod["spec"]
        njust = max_attr_len(spec, ["initContainers", "containers"], "name")

        if "initContainers" in spec:
            for c in spec["initContainers"]:
                print(" I", c["name"].ljust(njust), " ", "image:", c["image"])

        if "containers" in spec:
            for c in spec["containers"]:
                print(" C", c["name"].ljust(njust), " ", "image:", c["image"])

        print()


def hlp_scale(p, extra_args):
    args = apply_ns([], p)

    targets_contain_objtypes = True
    targets = []

    # extracts name from "name=replicas" definition
    def name_from_def(defstr):
        return defstr.split("=", 1)[0]

    # split extra_args to args and target object names
    for a in extra_args:
        if a.startswith("-"):
            args.append(a)
        else:
            targets.append(a)

            if "/" not in a:
                targets_contain_objtypes = False

    if not targets_contain_objtypes:
        # get names of all possible objects
        known_kinds = {}  # oair of: lowercase item_name -> array of lowercase kinds
        items = kubectl_items(
            ["get", "deployment,replicaset,replicationcontroller,statefulset", "-o", "json"] + args)
        for i in items:
            kind = i["kind"].lower()
            name = i["metadata"]["name"].lower()

            if name not in known_kinds:
                known_kinds[name] = []

            known_kinds[name].append(kind)

        for i, tgtdef in enumerate(targets):
            if "/" not in tgtdef:
                namekey = name_from_def(tgtdef).lower()

                if namekey in known_kinds:
                    kinds = known_kinds[namekey]
                    if len(kinds) == 1:
                        targets[i] = kinds[0] + "/" + tgtdef
                    elif len(kinds) > 1:
                        fail("ambiguous scale target " + namekey +
                             " with kinds " + " ".join(kinds))

    for tgtdef in targets:
        parts = tgtdef.split("=", 1)
        if len(parts) == 2:  # name=repl_num format
            exec_kubectl(["scale", "--replicas", parts[1], parts[0]] + args)
        else:  # name format (expect --replicas in args)
            exec_kubectl(["scale", parts[0]] + args)


h = register_helper("ev", "get events", [
                    "get", "events", "--sort-by", ".metadata.creationTimestamp"])
h = register_helper(
    "run", "run a new temporary deployment with a TTY attached", func=hlp_run)
h.add_argument("--name", help="pod name (default random)")
h.add_argument("-i", "--image", help="image to pull and run", default="alpine")
h.add_argument("-g", "--generator",
               help="generator to use for the deployment", default="run-pod/v1")
h.add_argument("--no-rm", default=False, action="store_true",
               help="do not remove container upon leaving the shell")
h.add_argument("--no-it", default=False, action="store_true",
               help="do not add -i -t arguments")

register_common_helpers("ns", "namespace", "namespaces")
register_common_helpers("po", "pod", "pods")
h = register_helper("po.names", "get the names of the matching pods", [
                    "get", "pods", "-o", "jsonpath='{.items[*].metadata.name}'"])
h = register_helper("po.first", "get the name of the first matching pod", [
                    "get", "pods", "-o", "jsonpath='{.items[0].metadata.name}'"])
h = register_helper(
    "po.top", "get table of processes for a pod", ["top", "pod"])
h = register_helper("po.co", "list containers of pod(s)",
                    ["get", "pods"], func=hlp_po_co)

h = register_helper(
    "po.x", "execute a command in the container (bash by default)", func=hlp_po_x)
h.add_argument("-c", "--container",
               help="container to run the shell in (the first one by default)")
h.add_argument("--no-it", default=False, action="store_true",
               help="do not pass -i -t to the kubectl exec (PTY)")

register_common_helpers("svc", "service", "services")
register_common_helpers("rs", "replicaset", "replica sets")
register_common_helpers("rc", "replicationcontroller",
                        "replication controllers")
register_common_helpers("sts", "statefulset", "stateful sets")
register_common_helpers("ds", "daemonset", "daemon sets")
register_common_helpers("cj", "cronjob", "cron jobs")
register_common_helpers("cm", "configmap", "config maps")
if ALLOW_SHORT:
    register_common_helpers("j", "job", "jobs")
    register_common_helpers("d", "deployment", "deployments")
    register_common_helpers("sec", "secret", "secrets")
else:
    register_common_helpers("job", "job", "jobs")
    register_common_helpers("deploy", "deployment", "deployments")
    register_common_helpers("secret", "secret", "secrets")
register_common_helpers("no", "node", "nodes", namespaced=False)
h = register_helper("no.top", "get table of processes for a node", [
                    "top", "node"], namespaced=False)
h = register_helper("no.res", "list nodes with resources requested on them", [
                    "describe", "node"], namespaced=False, func=hlp_no_res)
h = register_helper("no.po", "pods on a node(s)", [
                    "describe", "nodes"], func=hlp_no_po)

h = register_helper("no.drain", "drain node", [
                    "drain"], namespaced=False, func=hlp_no_drain)
h.add_argument("-C", "--complete", default=False, action="store_true",
               help="drain the node completely (implies --force, --delete-local-data and --ignore-daemonsets)")

h = register_helper("no.x", "execute command in remote node(s)",
                    namespaced=False, func=hlp_no_x)
h.add_argument("nodes", nargs="*", help="node names")
h.add_argument("-l", "--selector", help="node label selector")
h.add_argument(
    "-u", "--user", help="user to connect via ssh to", default="admin")
h.add_argument("-s", "--sudo", help="use sudo before command", default=True)
h.add_argument("-x", "--command", "--execute",
               help="remote command to execute", default="sh")

h = register_helper("no.df", "get node(s) disk usage", [
                    "get", "node"], namespaced=False, func=hlp_no_df)
h.add_argument("nodes", nargs="*", help="node names")
h.add_argument("-l", "--selector", help="node label selector")
h.add_argument(
    "-u", "--user", help="user to connect via ssh to", default="admin")
h.add_argument("-s", "--sudo", help="use sudo after logging in", default=True)

h = register_helper(
    "use", "set the working namespace or return the current one", namespaced=False, func=hlp_use)
h.add_argument("set_ns", help="namespace to switch to", nargs="?")

h = register_helper(
    "ctx", "switch kubeconfig context or return the current one", namespaced=False, func=hlp_ctx)
h.add_argument("set_ctx", help="context name to switch to", nargs="?")

h = register_helper("logs", "get container logs", func=hlp_logs)
h.add_argument("--tail", nargs="?", const=DEFAULT_TAIL,
               help="print this number of lines from the end")
h.add_argument("-f", "--follow", action="store_true",
               help="stream following lines")
h.add_argument("-p", "--previous", action="store_true",
               help="pritn the logs for the previous instance of the container if it exists")
h.add_argument("-l", "--selector", help="label selector")
h.add_argument("-c", "--container",
               help="container name of a multi-container pod")
h.add_argument("-r", "--raw", action="store_true",
               help="do not use pager (less/more), applies to non --follow log output only")

# in addition to "kubectl scale" arguments, it is possible to use short format with name=replicas
h = register_helper("scale", "scale deployment, replicaset, replication controller or statefulset", [
                    "scale"], func=hlp_scale)

h = register_helper("apply.f", "apply file",
                    namespaced=False, func=hlp_apply_f)
h.add_argument("file_or_url", help="file path or URL to the manifest to apply")

h = register_helper("del.f", "apply kustomization file",
                    namespaced=False, func=hlp_del_f)
h.add_argument(
    "file_or_url", help="file path pr URL to kustomization manifest")

h = register_helper("apply.k", "apply kustomization file",
                    namespaced=False, func=hlp_apply_k)
h.add_argument(
    "file_or_url", help="file path pr URL to kustomization manifest")


cmd_install = subparser.add_parser(
    "install-symlinks", description="install symbolic links")
cmd_install.set_defaults(func=make_symlinks)
cmd_install.add_argument("-t", "--target-path",
                         help="target path to install symlinks")

# common actions
if os.path.basename(sys.argv[0]) == "k":
    args = apply_ns(sys.argv[1:])
    exec_kubectl(args)
    sys.exit(0)
elif len(sys.argv) > 1:
    if sys.argv[1] == "install-symlinks":
        args = parser.parse_args()
        if hasattr(args, "func") and args.func != None:
            args.func(args)
        sys.exit(0)
    if sys.argv[1] == "-h" or sys.argv[1] == "--help":
        for h in symlink_helpers:
            for p in symlink_helpers[h]:
                print(p.description, end="\n ")
                p.print_usage()
        print()
        exec_kubectl(["--help"])
        sys.exit(0)

# attempt to run the helper command
if this_helper in symlink_helpers:
    matched = False

    for p in symlink_helpers[this_helper]:
        try:
            args, extra_args = p.parse_known_args(sys.argv[1:])
            args.func(args, extra_args)
            matched = True
            break
        except SystemExit:
            pass

    if matched != True:
        # for p in symlink_helpers[this_helper]:
        #    p.print_usage()
        sys.exit(45)
    else:
        sys.exit()  # should not go here normally (helper function has been called)

# run the kubectl command unmodified (we don't have a helper defined!)
argv = sys.argv[1:]
print("Warning: No helper " + this_helper, file=sys.stderr)
print("Warning: Running kubectl " + " ".join(argv) +
      " directly without " + SCRIPT_FILE_NAME, file=sys.stderr)
exec_kubectl(argv)
