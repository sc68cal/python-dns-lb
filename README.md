### Python DNS loadbalancer daemon

This is a python based DNS service, that takes DNS queries for
FQDNs, and returns DNS responses, based on what members in a
pool are available.


https://medium.com/dev-bits/a-minimalistic-guide-for-understanding-asyncio-in-python-52c436c244ea
https://uvloop.readthedocs.io/dev/index.html


## rqlite database

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
