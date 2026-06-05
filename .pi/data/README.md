# Allowed Targets

This folder stores safe target configuration for Topic 02.

## Why This Exists

Port scanning must be scoped. The pipeline should run only on:

- localhost
- lab machines
- targets you own
- targets you are explicitly authorized to test

## Current Config

The allowlist is stored in:

```text
.pi/data/allowed_targets.json
```

Safe default targets:

- `localhost`
- `127.0.0.1`
- `::1`
- `scanme.nmap.org`

## Manage Targets

List current targets:

```bash
python .pi/tools/manage_targets.py list
```

Add an authorized target:

```bash
python .pi/tools/manage_targets.py add 192.168.1.100
```

Remove a target:

```bash
python .pi/tools/manage_targets.py remove 192.168.1.100
```

## Temporary Authorization

For a target outside the allowlist, use `--authorized` only if you truly have permission:

```bash
python .pi/tools/main_pipeline.py --target 192.168.1.100 --authorized
```

## Safety Rule

Never scan a system you do not own or do not have permission to test.
