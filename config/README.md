# Piscan Configuration

This directory contains configuration files for Piscan.

## Files

- `config.example.yaml` - Example configuration with all options documented
- `config.yaml` - Your actual configuration (gitignored, create from example)

## Quick Start

1. Copy the example configuration:
   ```bash
   cp config/config.example.yaml config/config.yaml
   ```

2. Edit your configuration:
   ```bash
   nano config/config.yaml
   ```

3. Update at minimum:
   - `api.url` - Your API server URL
   - `api.token` - Your authentication token
   - `api.workspace` - Your workspace name

## Configuration Priority

Piscan looks for configuration in this order:

1. Path specified with `--config` flag
2. `./config/config.yaml` (project directory)
3. `~/.piscan/config.yaml` (user home directory)
4. `/etc/piscan/config.yaml` (system-wide)

The local `config/config.yaml` is recommended for development and single-user setups.

## Running with Local Config

```bash
# Automatic (looks in ./config/config.yaml first)
piscan server

# Explicit
piscan --config config/config.yaml server
```

## Important Settings

### Scanner Settings
- `device` - Leave empty for auto-detection
- `resolution` - 150, 300, or 600 DPI
- `source` - "Auto" recommended (tries ADF, falls back to Flatbed)

### API Settings
- `workspace` - Must match your API workspace
- `url` - Base URL without trailing slash
- `token` - Keep this secret!

### Storage Settings
- `temp_dir` - Where scans are temporarily stored
- `failed_dir` - Where failed scans are kept for retry

### Processing Settings
- `skip_blank` - Set to false to keep all pages
- `blank_threshold` - Lower = more aggressive blank detection (0.01-0.05)

## Security Note

**Never commit `config/config.yaml` to git!**

It contains your API token and should be kept secret. The `.gitignore` file
already excludes it.
