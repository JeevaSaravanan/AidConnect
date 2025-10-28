#!/usr/bin/env python3
import json, subprocess, sys

def send(p, obj):
    line = json.dumps(obj, separators=(",", ":")) + "\n"
    p.stdin.write(line.encode()); p.stdin.flush()

def recv(p):
    line = p.stdout.readline()
    return json.loads(line.decode())

def main():
    p = subprocess.Popen([sys.executable, "hub_server.py"],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=sys.stderr)
    send(p, {"jsonrpc":"2.0","id":1,"method":"initialize",
             "params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"local","version":"1.0"}}})
    print("initialize →", json.dumps(recv(p), indent=2))
    send(p, {"jsonrpc":"2.0","method":"notifications/initialized","params":{}})
    send(p, {"jsonrpc":"2.0","id":2,"method":"tools/list"})
    print("tools/list →", json.dumps(recv(p), indent=2))
    send(p, {"jsonrpc":"2.0","id":3,"method":"tools/call",
             "params":{"name":"disaster_plan","arguments":{"city":"New York","hazard":"flood"}}})
    print("disaster_plan →", json.dumps(recv(p), indent=2))

if __name__ == "__main__":
    main()
