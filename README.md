# Python DNS loadbalancer daemon

This is a python based DNS service, that takes DNS queries for
FQDNs, and returns DNS responses, based on what members in a
pool are available.

## Purpose

This was written to try out a couple of different technologies that
I have been meaning to experiment with for a couple years now. One
of the major features of recent versions of Python 3 that has been
the support for asynchronous programming within the language itself (as opposed to libraries like `twisted` or `gevent`), and the ecosystem of
libraries (like `aiohttp`) that take advantage of the new primitives that 
recent versions of Python 3 now provide.

I also wanted to try out `rqlite`, which has been on my radar for a
number of years. I always wanted to try it, but never had an opportunity
for greenfield development where I could build from the beginning with
`rqlite` in mind.


### Tech stack

It uses [asyncio][asyncio], the [`create_datagram_endpoint` API][datagram],
[rqlite][rqlite], [dnspython][dnspython], [aiohttp][aiohttp], and [uvloop][uvloop] (where supported).


## rqlite database

### rqlite development deployment
For development purposes, a single rqlite node can be run via `podman`

```shell
podman run -p4001:4001 docker.io/rqlite/rqlite
```

### rqlite production cluster

For a real deployment, you can use the [3 node k8s deployment][rquite-3-node].

If you are using [k3s](https://k3s.io) you will need to create a
PVC that uses the [`local-path` storage][local-path]

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

This project also relies on [foreign key constraints][fk], so the kubernetes YAML
for deploying `rqlite` also needs have the `fk` setting added.

```patch
21c21
<         args: ["-disco-mode=dns","-disco-config={\"name\":\"rqlite-svc-internal\"}","-bootstrap-expect","3", "-join-interval=1s", "-join-attempts=120"]
---
>         args: ["-disco-mode=dns","-disco-config={\"name\":\"rqlite-svc-internal\"}","-bootstrap-expect","3", "-join-interval=1s", "-join-attempts=120", "-fk=true"]
```

https://github.com/rqlite/rqlite
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


[asyncio]: https://docs.python.org/3.9/library/asyncio.html
[local-path]: https://docs.k3s.io/storage#setting-up-the-local-storage-provider
[rquite-3-node]: https://github.com/rqlite/kubernetes-configuration/blob/master/statefulset-3-node.yaml
[datagram]: https://docs.python.org/3.9/library/asyncio-protocol.html#udp-echo-server
[rqlite]: https://github.com/rqlite/rqlite
[dnspython]: https://dnspython.readthedocs.io/
[uvloop]: https://uvloop.readthedocs.io/dev/index.html
[aiohttp]: https://docs.aiohttp.org/en/stable/index.html
[fk]: https://github.com/rqlite/rqlite/blob/master/DOC/FOREIGN_KEY_CONSTRAINTS.md
