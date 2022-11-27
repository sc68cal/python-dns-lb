### Python DNS loadbalancer daemon

This is a python based DNS service, that takes DNS queries for
FQDNs, and returns DNS responses, based on what members in a
pool are available.


https://medium.com/dev-bits/a-minimalistic-guide-for-understanding-asyncio-in-python-52c436c244ea
https://uvloop.readthedocs.io/dev/index.html


## rqlite database

### rqlite development deployment
For development purposes, a single rqlite node can be run via `podman`

```shell
podman run -p4001:4001 docker.io/rqlite/rqlite
```

### rqlite production cluster

For a real deployment, you can use the [3 node k8s deployment](https://github.com/rqlite/kubernetes-configuration/blob/master/statefulset-3-node.yaml).

If you are using [k3s](k3s.io) you will need to create a PVC that uses
the [`local-path` storage](https://docs.k3s.io/storage#setting-up-the-local-storage-provider) 
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: rqlite-file
  namespace: default
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: local-path
  resources:
    requests:
      storage: 6Gi
```

Then modify the rqlite 3 node deployment the YAML slightly.

```patch
49c49
<       storageClassName: "standard"
---
>       storageClassName: "local-path"
```


### Schema and initial data

```shell
curl http://localhost:4001/db/execute -H 'Content-Type: application/json' -d @schema.json
```

```shell
curl 127.0.0.1:4001/db/execute -H "Content-Type: application/json" -d @populate_data.json
```

```shell
curl -G '127.0.0.1:4001/db/query?associative' --data-urlencode 'q=SELECT host FROM dns_zone_member JOIN dns_zone ON dns_zone_member.dns_zone = dns_zone.id WHERE dns_zone.name == "google.com."' | jq
```


### Functional tests

You can test the server with the `dig` utility, which comes as part of `bind-utils`
on most distributions. FreeBSD has it as part of the `dns/bind-tools` port.

```shell
dig @127.0.0.1 -p 9999 google.com
```
