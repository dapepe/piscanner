Raspberry Pi Canon DR-F120 Scanner Automation
=============================================

## Introduction

This document outlines a comprehensive plan to develop a Python-based scanning service on a Raspberry Pi for a Canon imageFORMULA DR-F120 document scanner. The application is called "piscan". The application will use the SANE scanning tools (via the scanimage command-line utility) to acquire images either from the automatic document feeder (ADF) or the flatbed (with automatic source detection if possible), skip blank pages, store scanned pages in a timestamped folder, and upload them to a remote API. It will run as a background service on the Pi, reacting to the scanner’s physical “Scan” button press and also exposing an HTTP interface for remote operation and monitoring. Configuration will be handled via a YAML file (for settings like API endpoint, auth token, image format, resolution, etc.), and robust logging with adjustable log levels will be included. A special test mode will help identify scanner button events to assist in mapping hardware buttons to actions.

Requirements Overview
- Scanning via SANE: Utilize scanimage (SANE backend) to perform scans. Support scanning from the ADF (for multipage documents) and flatbed platen. Ideally, implement automatic source selection if possible (use feeder if pages are loaded, otherwise flatbed).
- Empty Page Skipping: Detect blank or nearly-blank pages and skip them (do not include in output or upload).
- Storage Management: Save all scanned page images into a temporary timestamped directory (e.g. /tmp/2025-11-22-21:32:06/ for a scan performed at that date/time). This isolates each scan job’s images. (The temp base path can be configurable.)
- API Upload: After scanning is complete (all pages scanned), send an HTTP POST request to the remote endpoint (e.g. /api/document/) including all the image files for that document in one request. Authentication will use a Bearer token in the header.
- Physical Button Trigger: Detect when the scanner’s physical Scan button is pressed and automatically initiate the scanning/upload workflow. The application should register or listen for this hardware event so the user can start a scan by simply pressing the button on the device.
- Configurable Settings: Use a YAML configuration file to allow easy changes to parameters such as scanner device name, scan resolution (DPI), color mode (color/grayscale), image format (e.g. PNG, JPEG, TIFF), API URL, authentication token, storage paths, blank-page sensitivity, HTTP server port, etc.
- Logging: Implement logging with multiple levels (DEBUG, INFO, WARNING, ERROR). The service should log key events (scanner found, scan started/finished, pages scanned, blank pages skipped, files uploaded, errors, etc.) either to a log file or syslog. The log level should be adjustable via the config (for example, verbose DEBUG for troubleshooting, or INFO for normal operation).
- HTTP Control & Monitoring: Provide a lightweight HTTP server (REST API) for external control and status monitoring. At minimum, include an endpoint to trigger a scan manually (e.g. POST /scan) – which will start the scan job as if the button were pressed – and an endpoint to view logs or status (e.g. GET /logs for recent log output, or a simple status page). This allows remote triggering from a web interface or HTTP client and remote monitoring of the service’s activity.
- Button Test Mode: Provide a mode or command (e.g. running the script with --test-button) that helps determine if the scanner’s button press can be detected and identify which button was pressed. This is useful for configuring the button actions, especially since some scanners have multiple buttons (like “Scan”, “Copy”, “Email”). In test mode, the application should listen for button events and report/log which button triggers are received.

## System Architecture Overview

To meet these requirements, the system will be composed of several coordinated components:
- Scanning Component: Handles communication with the scanner through the SANE API (using scanimage). It will issue scan commands with appropriate options for source, resolution, and format. For multipage scanning, it will leverage SANE’s batch mode to scan all pages from the feeder automatically. The scanning module will also perform blank page detection on each scanned image (or after scanning) to filter out empty pages before upload.
- Temporary File Manager: Manages the creation of a timestamped directory for each scan session and the cleanup of image files. When a scan is initiated (via button or HTTP), a new folder like /tmp/<YYYY-MM-DD-HHMMSS>/ will be created to store that job’s images (e.g. 2025-11-22-213206_page1.png, ..._page2.png, etc.). After a successful upload to the server, the images can be deleted or archived as needed to free space (this could be a configurable behavior).
- Uploader Component: After scanning, this component will collect all image files for the document and perform an HTTP POST to the configured API endpoint. It will attach all images in a single request (using a multipart/form-data request with multiple file fields). The request will include the Authorization: Bearer <token> header for authentication (the token being read from the config). On success (HTTP 200 OK or similar), it may log a confirmation and trigger cleanup of the temp files. If the upload fails, it will log an error and possibly retry or save the files for later retry (depending on design decisions or config for retries).
- Button Event Listener: A mechanism to detect the scanner’s physical button presses. Because scanner hardware buttons are not directly accessible via simple OS events, we plan to integrate the Scanner Button Daemon (scanbd) for this purpose. The scanbd service can poll the scanner for button presses and trigger actions when a button is pressed ￼ ￼. In our architecture, scanbd will be configured to execute a custom action (like calling our application’s scan trigger, e.g. via an HTTP request or a script) when the “Scan” button is pressed. This allows the main Python application to remain idle until a button event occurs, then wake and perform scanning. (See the Physical Button Handling section for details.)
- HTTP Server: A small HTTP server (built with a Python framework like Flask or FastAPI) will run within the application. This server will provide endpoints to trigger scans and to fetch logs/status. For example:
- POST /scan – triggers the scanning process (if the scanner is idle). The server handler will initiate a new scan job by calling the scanning component. It can respond immediately with a status (e.g. “Scan started”) or wait until completion to return results (e.g. number of pages scanned or any error info). In practice, it might be better to start the scan in a background thread and return immediately, to not block the HTTP request for long scanning durations.
- GET /logs – returns recent log entries or the entire log file (possibly just as plain text or JSON). This allows an admin to quickly check the scanner’s activity remotely. (We might restrict the size or implement pagination if the log is large.)
- Potentially GET /status – returns a simple status JSON (e.g. {"scanner":"ready","last_scan":"2025-11-22T21:32:30","last_result":"success"} etc.) indicating if idle or busy. (This is an optional enhancement.)
The HTTP server will run on a configurable port (default could be 5000 or 8000) and bind to either localhost or all interfaces depending on use case (for example, binding to LAN interface if remote access is needed). Since the API is likely for internal use, we may not implement heavy authentication on it, but if needed, a simple API token or basic auth could be added for the HTTP endpoints.
- Configuration Manager: A module to load and parse the YAML configuration file at startup. It will supply all other components with the needed settings (scanner device name, resolution, etc.). We’ll use PyYAML in Python to parse the YAML file into a dictionary or object for easy access in code. The config file provides an easy way for the user to adjust parameters without modifying code. Example config options:
- device: "canon_dr:libusb:001:002" (SANE device name of the scanner – discovered via scanimage -L)
- resolution: 300 (DPI)
- mode: "Color" (or "Gray" for grayscale scanning)
- source: "ADF" (could be "Flatbed", or an "Auto" mode if we implement automatic source detection)
- format: "png" (image format for output files; could also be "jpeg" or "tiff". SANE’s scanimage supports PNM by default, and TIFF/PNG/JPEG with --format flag ￼.)
- api_url: "https://myserver.com/api/document/"
- api_token: "ABC123XYZ" (the Bearer token for Authorization header)
- temp_dir: "/tmp" (base path for temporary storage)
- skip_blank: true and blank_threshold: 0.03 (for 3% non-white pixel threshold – meaning if ≤3% of pixels are non-blank, consider page blank. This threshold is configurable; e.g. 0.03 = 3%, corresponding to 97% of the page being white ￼.)
- log_file: "/var/log/scanner_app.log" (optional path for log output)
- log_level: "INFO" (logging verbosity)
- http_port: 5000
- etc.
- Logging: The Python built-in logging module will be used to implement logging. We will set up a logger that writes to a file (and/or console). The log format can include timestamps, severity level, and message. Different parts of the application (scanner, uploader, http server) will log through this common logger. The config’s log_level will determine the minimum severity to record (DEBUG for full detail including low-level operations and SANE command outputs, INFO for high-level events, ERROR for only errors, etc.). We might also log to syslog if running as a service on Raspberry Pi for easier system integration. The HTTP /logs endpoint can read from the log file or maintain an in-memory ring buffer of recent messages. Additionally, during development or troubleshooting, running the app in foreground with DEBUG logging will help see the flow of actions.

With these components in mind, the application will operate as a daemon (background service). On startup, it will load the config, initialize logging, verify it can communicate with the scanner (perhaps by listing devices or doing a test scan), start the HTTP server, and then wait for triggers (either an HTTP request or a button press event via scanbd). When a scan is triggered, it will perform the scanning and uploading, then go back to waiting for the next trigger.

The following sections detail key aspects of the implementation, including how scanning is performed, how blank pages are detected, how we handle the scanner’s button, and setup instructions for the environment.

## Scanning Functionality

SANE and scanimage – We will use the SANE (Scanner Access Now Easy) backend which has command-line tools available. The primary tool is scanimage, which allows controlling the scanner via terminal commands. We choose this rather than a Python SANE library for simplicity and reliability, since scanimage is well-tested. The Canon DR-F120 is supported by SANE through the canon_dr backend (device ID 0x1083/0x1654) – according to SANE’s device list, the ADF (document feeder) works with this backend, while flatbed support is limited ￼. Thus, our implementation will emphasize feeder scanning. (If flatbed scanning on Linux is not functional for this model, the “automatic input recognition” might effectively fall back to just using the feeder. We will note this in documentation and allow a manual selection of source in config if needed.)

To find the scanner and ensure SANE recognizes it, we can use:

  scanimage -L

This will list connected scanner devices. For example, it might output:

  device `canon_dr:libusb:001:002' is a CANON DR-F120 scanner

as shown in a Raspberry Pi environment ￼. The string before the quote is the device name to use. In our app, the user can either specify this device in the YAML config, or if left blank, we can default to the first detected scanner. (The SANE API also allows setting SANE_DEFAULT_DEVICE env var or simply using the first available device if none specified ￼.)

Scan Resolution and Mode – The config will allow setting the DPI (common values: 150, 300, 600) and color mode. We will pass these to scanimage via options like --resolution 300 and --mode Color (or Gray for grayscale). These options correspond to those exposed by the backend – running scanimage -h will show supported modes and resolutions for the device ￼ ￼. The DR-F120 likely supports color and grayscale; we’ll default to color unless configured otherwise.

Selecting Source (ADF vs Flatbed) – The application will by default use the ADF for scanning multiple pages. We can specify --source "ADF" or the exact source name if needed. Some SANE backends support an “Automatic” source mode that auto-selects the feeder if paper is present, otherwise the flatbed; for example, certain Brother scanners list an --source Automatic Document Feeder vs Flatbed ￼. We will research if the Canon’s backend has an “Auto” source. If it does, we can use that for convenience. If not, our strategy for auto input recognition will be: attempt an ADF scan, and if it fails or returns no pages (perhaps feeder empty), then fall back to scanning from flatbed. This could be done by checking the scanner status after trying feeder, or by using a small “pre-scan” check if possible (not all backends provide a status for paper loaded). Alternatively, the user can configure the source explicitly in the YAML (source: ADF or source: Flatbed) if they know what they want.

Batch Scanning for Multiple Pages – To scan multiple pages from the feeder in one go, we will use scanimage’s batch mode options. scanimage can continuously scan from the ADF until empty, writing each page to a separate file. For example:

  scanimage --batch=out_%03d.png --format=png --source ADF --resolution 300 --mode Color

This command would scan page-by-page, saving files as out_001.png, out_002.png, etc., until the feeder is out of pages. The --batch option accepts a filename pattern (with a %d placeholder for page numbers) and will keep scanning sequentially ￼. If no pattern is given, it defaults to out%d.pnm (or appropriate extension if format specified) ￼. We will construct the pattern to save into our timestamped directory, e.g. "/tmp/2025-11-22-213206/page_%02d.png" for numbered page files.

One consideration: not all scanners reliably report the “ADF empty” condition to SANE. If the backend doesn’t signal end-of-document, scanimage --batch might hang waiting for more pages. In such cases, SANE allows specifying a maximum count with --batch-count. We prefer to let it run until empty by default (so the user doesn’t have to pre-specify number of pages), but we will implement a timeout or use --batch-count if we detect issues. According to documentation, if --batch-count is not given, “scanimage will continue scanning until the scanner returns a state other than OK”. However, “Not all scanners with document feeders signal when the ADF is empty, [you can] use this command to work around them” ￼. For the DR-F120, we’ll test if it stops automatically when feeder is done. If not, we might set a reasonable max (or instruct the user to press “Cancel” on the device if available). This can be refined based on testing.

During scanning, we can enable progress reporting (with -p flag) if we want to log the progress, but that may be too granular. Instead, after each page file is created, our code can log “Scanned page 1, 2, …”.

File Format – We will support saving images as PNG or JPEG (or TIFF). PNG is lossless and good for text (and supported by scanimage as an output format ￼), while JPEG could be used if file size is a concern (at the cost of compression artifacts, especially for text). TIFF is another option (especially if we later want to assemble a multi-page TIFF or PDF). By default, we might choose PNG for crisp image quality. The user can set file_format in config, and we’ll pass --format accordingly (--format=png or --format=jpeg, etc.). If jpeg is used, we might also allow setting JPEG quality (some SANE backends might have a separate option for compression quality, or we can post-process the image). For simplicity, PNG (which uses lossless compression) is a solid default. Note: If --format=tiff is used with --batch, scanimage will produce a series of TIFF files, one per page, not a single multi-page TIFF – combining them would be another step, so it’s similar to handling PNGs. There is no built-in PDF output from scanimage (we’d have to convert if needed) ￼, but since the requirement says images are sufficient, we won’t generate PDFs in this implementation (though that could be an extension).

Blank Page Detection – After each page is scanned (or after the entire batch), the application will analyze images to identify blank pages and drop them. We have multiple methods to do this:
- The simplest approach is to look at the image’s content histogram or pixel statistics. We can load the image using a library like Pillow (PIL) in Python. Convert it to grayscale and compute how many pixels are nearly white. For example, define a threshold (like if a pixel’s brightness > 250 out of 255, consider it “white”). Count the fraction of pixels that are non-white. If that fraction is below a certain threshold, we deem the page blank. For instance, if >99% of the pixels are white, it’s blank. The threshold (e.g. 0.97 or 97% white) can be tuned in config (blank_threshold). This approach is fast and straightforward. It may incorrectly drop pages that have a tiny amount of content (like a lone dot or a faint letterhead), but we can calibrate the threshold to avoid false positives. The scanPDF tool by Virantha uses 97% as default (meaning if a page is 97% white it’s considered blank) ￼.
- Another approach is to use image metadata like file size or unique color count. For example, if scanning to compressed TIFF/PNG, a truly blank page compresses very well and results in a much smaller file size. One could set a file size cutoff – but this can be unreliable depending on compression and noise. A more robust measure is counting unique colors: a blank page (white background only) will have very few unique colors (maybe only white). ImageMagick’s identify tool with %k format can count unique colors ￼, but using Pillow directly we can also do this or simply count non-white pixels which is effectively similar.
- SANE built-in skip: Some scanner drivers have a built-in “Skip Blank Pages” option, but often it’s not accessible or marked inactive via SANE ￼ ￼. (In one example, a Brother ADF scanner showed --SkipBlankPage in options but it was inactive unless specific conditions are met.) We will not rely on the scanner’s internal blank detection, as it may not be enabled by default. Instead, our software method will handle it. We will allow the user to disable our blank-page removal (keep_blanks: true) in case they want to keep all pages (for instance, if double-sided scanning where backside might be intentionally left blank – but typically that’s exactly when you do want to drop blanks).

Implementation detail: after scanning a batch, we will iterate over the image files in the temp folder. For each, perform the blank check. If a file is deemed blank:
- We can either delete it immediately, or move it to a subfolder (e.g. blanks/) for record-keeping. Deleting is straightforward, but moving to a blanks folder for review could be a nice debugging feature. Perhaps controlled by a debug setting.
- We will also decrement the page count for upload and log that “Page X was blank and skipped.”

By removing blank pages, we ensure they are not uploaded. This saves bandwidth and storage on the server side. (If the API expects a certain page count or has its own blank detection, we should confirm requirements – but since the user explicitly requested skipping, we’ll implement it on our side.)

## Temporary Storage and File Management

Each scan job will have its own directory named with a timestamp of when the scan started. For example: if a scan is initiated on 2025-11-22 at 21:32:06, a directory /tmp/2025-11-22-21:32:06/ will be created (or using an ISO format 2025-11-22T213206 without colons, since colon is not typically allowed in Windows paths but on Linux it’s fine; to be safe, we may use underscores or omit punctuation). Inside this directory, scanned images will be saved as they come in (e.g. page_1.png, page_2.png, ... or similar naming). The naming convention can include the page number, which scanimage --batch can provide automatically with a %d placeholder ￼. We will likely set --batch=page_%02d.png to produce files page_01.png, page_02.png, ... etc. If multiple scans are triggered back-to-back, each gets a unique folder to avoid name collisions. The timestamp approach inherently does this.

After a scanning session is done and the files are uploaded successfully, the application should clean up the files to avoid filling the disk. We can remove the entire directory for that job. In case of an upload failure, we might keep the files (and log a warning) so that they can be retried or manually inspected. We might implement a retry mechanism or a separate “uploader queue” for robustness, but that could be overkill unless the environment is unreliable. A simpler approach: if upload fails, don’t delete the files, and allow a manual or next-run attempt to resend (perhaps with a command or automatically on next service start scan for leftover dirs). This is an edge-case detail that can be decided in implementation; the important part is to avoid indefinite accumulation of temp files.

The base temp directory (/tmp by default) can be configured via YAML (temp_dir). On Raspberry Pi, using the /tmp (which might be memory-limited) is okay for moderate volume, but if scanning many pages at high DPI (color), the images could be large. If memory is a concern, an alternative path (like an external storage or /var/spool/scans) could be used. We’ll let the user adjust that path. Each scan directory name will be derived from current datetime. For readability, we use Year-Month-Day-HourMinuteSecond. Another option is to use an incrementing job counter or a UUID; timestamp is fine since even multiple scans in the same second is unlikely, and if it happens, we can append a small random suffix.

## Uploading Scanned Pages to Remote API

Once we have the set of image files (minus any blanks) ready, the next step is to transmit them to the remote server’s API. The API expects a POST request to /api/document/ containing all image files that belong to this document. We will use Python’s requests library to construct this POST request. Using requests with multipart file upload is straightforward: we prepare a files payload. For multiple files, we can either give each a distinct field name or use the same field name multiple times. The exact requirement isn’t specified, but a common approach is to use a field like files[] or just repeat file field. For example, using requests:

```
files_payload = [
    ('file', open('page_1.png', 'rb')),
    ('file', open('page_2.png', 'rb')),
    # ... all files
]
response = requests.post(api_url, headers={'Authorization': f'Bearer {token}'}, files=files_payload)
```

This sends multiple files with the same field name “file”. Many APIs that accept multiple uploads allow this format. (If the API expects a different field name or one file at a time, we’d adjust accordingly, but the prompt implies sending all images in one call.) In Python requests, passing a list of tuples as above will attach each file under the same field key ￼. We should confirm with the API documentation if they expect files[] or similar; if needed, we can name them files[0], files[1], etc., but often simply repeating is fine.

We must also include the Bearer token. That will be done via the HTTP Authorization header: "Authorization: Bearer <your_token_here>". The token string will be read from config (for security, ensure this is kept safe – though in YAML it will be plain text, perhaps the Pi is in a secure environment). Using requests, setting this header is done as shown above. The Bearer token mechanism means the server will verify our token and decide if the request is authorized ￼. If the token is missing or wrong, the server would typically respond 401 Unauthorized, which we should catch and log as an error (and perhaps not retry until config is fixed).

We will implement error handling around the HTTP request:
- If response.status_code indicates success (e.g. 200 or 201), log an INFO that upload succeeded (maybe include the number of files/pages). Then proceed to cleanup files.
- If it indicates failure (>=400), log an ERROR with the status code and response text (if any) for debugging. Possibly attempt one retry after a short delay in case it was a transient issue. But since this is a scanning service (not high-frequency), manual intervention might be fine. We could mark the job as “failed” and leave images on disk for later resend.

Depending on network conditions, the upload of many images (especially if high resolution color scans) might take some time. During this time, if another scan is triggered, how do we handle it? We could queue the scans (i.e. if a scan is ongoing including uploading, either refuse new triggers or queue them). To keep it simple: we might allow only one scan job at a time. The HTTP /scan endpoint could check if a job is in progress and, if so, respond with a 409 Conflict or a JSON indicating “busy, try later”. Similarly, if the physical button is pressed while a scan is in progress, we might ignore it or queue it. A basic approach: use a global lock or flag scanning_in_progress. When a trigger comes in, if this flag is true, just log “Scan requested but another is in progress – ignoring”. This prevents overlapping commands to the scanner or overload.

If we wanted to be more fancy, we could queue and run sequentially. But likely the user will not attempt back-to-back scanning until the first is done (the feeder can only do one set at a time physically as well).

Security considerations: The communication with the API should ideally be over HTTPS (the URL likely is, given the example). We should verify SSL certificates by default (requests does that). The token should be kept secret; since it’s in config, ensure file permissions are such that only the intended user can read it. If multiple people use the Pi, that matters. Also, the HTTP control interface we expose – if we bind it to more than localhost, it could be a minor security risk (someone could trigger scans or read logs). If needed, we could restrict it to localhost and then only the user can SSH tunnel or something. Or implement a simple auth (maybe reuse the same Bearer token or a separate password for the web UI). This might be overkill, but worth noting.

## Logging Implementation

The application will produce logs to assist in monitoring and debugging. Key events to log:
- Service startup: configuration loaded, scanner device found (or if not found, log an error and maybe retry periodically until available).
- For each scan job: when triggered (and by what: “Button press” or “HTTP request”), the directory created, scanning options used (DPI, mode, source).
- Page-by-page progress: can log “Scanned page X” and if blank, “Page X is blank, skipped”.
- Completion of scanning: “Scan job completed, N pages scanned (M pages after skipping blanks).”
- Upload attempt: the URL (perhaps not including token), number of files, and result of the request. On success: “Uploaded N pages to API successfully (response code 200)”. On failure: log the HTTP code and perhaps first 200 chars of the error response for insight.
- Cleanup: “Temporary files deleted for job …”.
- Any exceptional errors: SANE command errors (if scanimage returns non-zero exit status or writes to stderr, capture that), timeouts, etc.

We will likely use a rotating log file or a single log file. If single, it can grow; but scanning isn’t extremely frequent, so it might be fine. Or we can integrate with systemd logging (just printing to stdout/err and letting systemd capture it). However, since we also want to serve logs via HTTP, having our own file to read is convenient.

The logging level can be set in config. In DEBUG mode, we might include even more granular logs or SANE debug info. Notably, we can run scanimage with environment variables to debug SANE (e.g. SANE_DEBUG_DLL=5 or SANE_DEBUG_CANON_DR=5 to get scanner driver debug output) ￼. We wouldn’t normally do that unless diagnosing a scanner issue, but having the ability (maybe via an environment variable or a debug flag) could be useful.

The HTTP /logs could simply read the last X lines of the log file. We might implement it to tail the file (for example, read the entire file and send it – if it’s small – or seek from end for last few KB to limit size). Since this is primarily for ease of use, we won’t build a fancy log viewer; just raw text output is acceptable (perhaps enclosed in <pre> tags if we serve it as HTML, or just as plaintext with content-type text/plain).

## Handling the Scanner’s Physical Button

One of the critical features is responding to the scanner’s “Scan” button. On many scanners, pressing the button by itself does nothing in Linux unless a service like scanbd is configured. The DR-F120’s buttons (it may have one or more – possibly just a scan start/stop) are supported by the SANE backend in principle, but there’s no direct kernel input event for them. Instead, the SANE backend might expose the button state as an option. Indeed, SANE has the concept of “button options” – you can see them by running scanimage -A (list all options) which “lists all available options exposed by the backend, including button options” ￼. In some cases, the button press toggles an option that scanbd can catch.

Using scanbd: We will leverage Scanner Button Daemon (scanbd), which is a specialized daemon that monitors scanner hardware for button presses and triggers scripts. How it works: scanbd continually polls the scanner through SANE (thus “occupying” it while polling), and when a button event occurs, it executes a predefined action (like running a script) ￼ ￼. Because scanbd holds the device, normal applications can’t access the scanner at the same time. To solve this, scanbd uses a proxy mode with scanbm (a manager) and forces other apps to use the network SANE interface to coordinate access ￼. In practice, setting up scanbd involves configuring SANE to use the “net” backend to localhost for normal scanning, so that scanbd can relinquish control when a real scan happens. This is a one-time configuration we must do on the Pi:
- SANE config for scanbd: Edit /etc/sane.d/dll.conf to only include net (comment out others) ￼, and in /etc/sane.d/net.conf add localhost ￼. This means any scanning action will go through the network loopback to scanbd (which listens on port 6566 by default). Then, configure /etc/scanbd/scanbd.conf with the actual backend (canon_dr) so that scanbd can directly access the scanner locally (we copy the config files to /etc/scanbd/sane.d/ as needed) ￼ ￼. This setup is a bit intricate but fortunately only done once. The ArchWiki provides a thorough guide which we can adapt ￼ ￼.
- scanbd Actions: In scanbd’s config, we define actions for button presses. For example, an action might be named “scan” tied to the scanner’s “Scan” button. Many scanners send a signal that can be filtered by name or number. The ArchWiki example shows an action triggered by a value change matching ^scan regex ￼. The Canon DR series might use similar naming. We might find a pre-made config for Canon in /etc/scanbd/scanner.d/ (there are includes for hp, epson, pixma, etc. ￼; possibly canon_dr might use the avision.conf or snapscan.conf if similar). If none, we create our own.
For our case, we’ll configure scanbd so that when the Scan button is pressed, it will run a custom script – say /etc/scanbd/scan.sh. This script will simply trigger our Python application to start scanning. There are a couple ways to trigger:
- Easiest: have the script call our HTTP endpoint. For instance, curl -X POST http://localhost:5000/scan (assuming our app listens on 5000 and accepts that). This is straightforward and decouples the processes (scanbd just makes an HTTP call).
- Alternatively: have the script call a command that signals our app. If our app were monitoring some IPC (like a UNIX socket or a file), it could do that. But since we already have an HTTP interface, using it is pragmatic.
- Another alternative: not use a script at all but run our scan command directly from scanbd. We could write a standalone script that does the scanning and uploading (bypassing our Python service entirely) and let scanbd invoke that. But that would duplicate functionality and complicate sharing state with the HTTP server. Better to funnel everything through one app.
Therefore, we likely choose the curl to HTTP approach for integration. We’ll include the installation of curl if not present (most likely it is).
Scanbd’s config action might look like:

```
action scan {
    filter = "^scan.*"        # regex to match the "Scan" button event (this depends on Canon’s backend naming)
    numerical-trigger {
        from-value = 1
        to-value   = 0
    }
    desc = "Scan to app"
    script = "/etc/scanbd/scan.sh"
}
```

This is analogous to the Arch example where a transition from 1 to 0 of a “scan” option triggers it ￼. The script /etc/scanbd/scan.sh would contain something like:

```
#!/bin/bash
curl -X POST -H "Content-Type: application/json" -d '{"source": "button"}' http://localhost:5000/scan
```

(We can decide if we need to send any data; simply hitting the endpoint might suffice, or we can include a JSON indicating it was triggered by button, in case our app wants to differentiate source for logging.)
We will ensure this script is executable and test it.

- Detecting Multiple Buttons: If the scanner had more than one button (e.g., one for “Scan to email” vs “Scan to file”), scanbd could detect different triggers via different filter regex (for example, maybe the driver reports a different option or value for each button). The user requested a way to “determine which button is pressed”. To facilitate that, we can use a test mode in which we configure scanbd (or use the existing config) to log the button events without actually scanning. The ArchWiki suggests a test.script which logs environment variables when triggered ￼. In fact, the default test.script in scanbd just writes all environment vars to a file (/tmp/scanbd.script.env) when an action fires ￼. Among those variables, SCANBD_ACTION or others would reveal what was pressed (often the action name like “scan” or maybe an index). We can guide the user to run scanbd in debug mode (e.g. sudo scanbd -f -d7 for foreground with debug level 7) and press buttons to see what events come through, or check the /tmp/scanbd.script.env. For example, after pressing a button, SCANBD_ACTION might be set to “scan” or some code, and SCANBD_DEVICE will show the device name ￼.
For our application’s test mode, we can simply piggyback on this: the app can instruct the user to press a button and then read the file or logs. Or we could integrate by temporarily using scanimage -A in a loop to see if any option changes. However, using scanbd’s established mechanism is more reliable. So our documentation will include: run the service in test mode which sets up scanbd with a test script to print the button info (or just manually configure and observe logs). Since this is mostly a one-time setup to identify the button code, it can be a semi-manual step documented rather than fully automated in code.
- After detecting which button corresponds to what, we will typically only use the main “Scan” button to trigger our scans. If there were multiple, we could map them to different behaviors. (e.g., “Button 1: scan and upload to API” which we are doing; “Button 2: maybe scan at a different resolution or to a different endpoint” – the user didn’t request this, but being “open to suggestions”, our design could allow multiple actions. For instance, config might allow defining profiles per button. However, unless needed, we’ll stick to one action for simplicity.)

Important: Because scanbd locks the device when running, we need to ensure coordination. Typically, when our app receives the trigger (via curl), it will then attempt to use scanimage. But if scanbd is still polling, that could conflict. This is exactly what the scanbd manager mode handles: when we use the net backend in our app’s scan, the request goes to scanbd (scanbm) which then pauses polling and hands off to saned. In other words, our Python app, instead of using device canon_dr:libusb:001:002 directly, might need to use the network device net:localhost:canon_dr:libusb:001:002. This is a crucial detail: If we configure SANE on the Pi such that only net is available (as described earlier), then any scanimage call in our app should be prefixed with device = net:localhost:<device>. Alternatively, we run scanimage -L which will now list a net:localhost:canon_dr:libusb:.... The Arch forum example showed that once scanbd was in place, doing a direct scanimage without specifying net resulted in “no SANE devices found” ￼, because local direct access was disabled. The solution was to explicitly use the net interface or ensure scanbd config is correct ￼ ￼. So, in implementation, we might do one of two things:
- Easiest: always call scanimage with the -d net:localhost:<devname> when starting a scan. We can get <devname> from initial listing or config. This forces using scanbd’s proxy. Or set SANE_DEFAULT_DEVICE to net:localhost:<dev> for our process.
- Alternatively, we could dynamically toggle: If not running with scanbd, use direct; if scanbd is active, use net. However, it might be simpler to just always use net:localhost (even if scanbd isn’t running, the net backend will fail if scanbd isn’t listening, so we should detect that).

We should mention this in documentation for setup: “When scanbd is used, local SANE access is via the network interface. Our application will be configured accordingly.” After proper setup, a manual test would be: scanimage -d net:localhost:canon_dr:libusb:001:002 --format=png > test.png should successfully scan via scanbd.

Test Mode for Button Detection: We plan to include a command-line flag (e.g. --test-button) for the Python app. What it can do is simply subscribe to button events and print them. This could be done by temporarily starting scanbd with a test config or by using SANE’s --all-options. However, invoking scanbd from our app is complex (needs root typically and config). Instead, we might instruct the user to use the system’s scanbd directly. Possibly our test mode could run scanimage -A repeatedly: Pressing the button might change an option (some scanners have an option like button-1 that goes from 0 to 1 momentarily). If we poll scanimage -A every second, we might catch a change. But that’s not guaranteed and is hacky.

It might be sufficient to document how to use scanbd’s logging for this. Since the user explicitly wants a “test command in the application”, perhaps we can integrate: For example, in test mode, we could run scanbd in the foreground (using Python’s subprocess) with a minimal config that triggers our Python callback for any button and print. But effectively that’s re-implementing what scanbd does on its own.

Alternatively, if the DR-F120’s backend supports an option for the button, we might directly use PyUSB to listen for interrupts – but that’s way too low-level and not needed if scanbd works.

So, we will document that the test mode will likely rely on scanbd: “It will monitor for a button event and report which action was triggered.” This likely means the user should press a button and then see console output like “Button ‘scan’ pressed detected”. Achieving this could be done by temporarily modifying scanbd.conf to call a script that communicates back. But to keep our development simpler, the test mode could instruct: “Please ensure scanbd is running in debug mode. Press the button and watch the logs or the output for which action is triggered.”

Given the user story, they might expect the test mode to simply output something like: “Detected button: Scan”. We can fulfill that by parsing scanbd’s output or environment. Perhaps the easiest: run scanbd -f in a subprocess from our app and parse its output for lines like “scanbd: begin of scan action…” etc. However, scanbd requires root privileges and system config. It’s tricky to spawn it reliably from userland.

Instead of over-engineering this, a clear setup documentation (next section) will guide how to test the button using scanbd’s standard method (which might be acceptable for the user).

In summary, handling the button press involves setting up scanbd and integrating it with our app via an HTTP call or similar. We’ll provide the necessary config snippets and instructions as part of the deployment.

## HTTP Server Design

We have chosen Flask (for example) to implement the HTTP interface. The server will run on a separate thread (Flask’s built-in server is single-threaded by default, but for our simple use that may suffice; we can also enable threaded mode or use gevent if needed to handle simultaneous calls – but our usage will be very low QPS, so it’s fine). When a POST /scan request comes in, the handler will:
  1.  Check if a scan is already in progress (a global flag). If yes, respond with 409 or a message “Scanner busy”. If no:
  2.  Possibly read JSON body or parameters (though for our case, we might not need any data from the request, unless we allow the requester to override certain config like resolution or source – which could be a feature but not required).
  3.  Log that a remote scan was requested.
  4.  Start the scanning process. This could be done inline (just call the function that runs scanimage and waits). But that could take tens of seconds, and the HTTP client might timeout. A better pattern is to offload the scan to a background thread and immediately return a response. For instance, use Python’s threading or concurrent.futures to start a new thread that runs the scan job function. The /scan endpoint can then return something like { "status": "started", "job_id": "<timestamp>" } right away. The actual scan job will proceed in background, and the result will be only in logs (or we could have a way to query it via status later).
- If we want to be fancy, we could maintain a small list of recent jobs and their status (in memory) so that the HTTP API could have /status/<job_id> to query if done. But unless someone plans to trigger multiple scans without watching logs, this might be unnecessary.
- Simpler: when /scan returns “started”, the user can watch the logs or just know it’s happening. If they hit /scan again too soon, they’ll get “busy” anyway.
  5.  The scanning thread will perform exactly what the button trigger code would – calling scanimage, processing images, uploading, etc. Since it’s running in the same app, it can call the same functions.
  6.  Possibly, after finishing, if we had job tracking, it could mark the job as done and success/failure.

For the GET /logs endpoint, we need to ensure thread-safety if it reads the log file while the scanning thread might be writing. But reading a file being written is okay (you might get partial data if not careful). We can implement a quick solution: open the log file, seek to end - N bytes to get the last few KB (or read all if size is small), then close. Or use Python’s tail -n equivalent by reading lines and taking the last 100 lines. Since this is not performance critical, we can just read all and slice in memory if needed.

Alternatively, we might keep an in-memory buffer of logs by attaching a custom logging handler (like logging.handlers.MemoryHandler or just a simple list) for recent messages. But that’s more complexity – reading the file is straightforward.

The HTTP endpoints will not require authentication by default (assuming this is on a private network or localhost). If exposure is a concern, we could restrict it or require a token (the same API token, but that might be problematic to reuse if the API token is meant for the remote server, not for our local API). We can optionally have a separate config for a simple API key to protect these endpoints.

We will document how to use these endpoints (with example curl commands):
- e.g. curl -X POST http://<raspi>:5000/scan to start scanning.
- curl http://<raspi>:5000/logs to fetch logs.

Optionally, we could provide a minimal HTML page for logs (just preformatted text) accessible via browser.

## Configuration and Setup Guide

To deploy this solution on the Raspberry Pi, follow these steps:

1. Install Scanner Drivers and Tools: Make sure the SANE backend for Canon DR-F120 is installed. On Raspberry Pi OS (Debian-based), install the sane utilities and scanbd:

```
sudo apt-get update
sudo apt-get install -y sane-utils scanbd python3-pip
```

This will install scanimage and related SANE drivers, as well as scanbd. Verify the scanner is recognized with scanimage -L. You should see the DR-F120 listed ￼. If it’s not found, you may need to install an updated SANE or a Canon driver package (Canon sometimes provides a Linux driver .deb – ensure it’s installed if needed, as some forum posts suggest). Also ensure your user is in the scanner group or appropriate permissions set (by default, saned or group “scanner” might own the USB device; you can add the pi user to group scanner or run the scanning commands as root to test).

If the scanner is not immediately supported by the stock SANE version, consider upgrading SANE to the latest version (the bugfix mentioned on Launchpad for DR-F120 might be in newer versions【0†】). For now, assume it’s working since the user indicated it was used.

2. Install Python Dependencies: Our application will use some Python libraries. Install them via pip:

  pip3 install pyyaml flask requests pillow

(pillow for image processing to detect blanks; Flask and requests as discussed; PyYAML for config.)

3. Configure SANE for scanbd: This is crucial for button support. We need to reroute SANE’s default behavior to let scanbd intercept. Edit /etc/sane.d/dll.conf – comment out all lines and just leave:

net

This means the only backend initial scan clients use is the net backend. In /etc/sane.d/net.conf, add:

```
connect_timeout = 3   # (optional timeout setting)
localhost
```

This tells the net backend to look at localhost for a saned service (which scanbd’s manager will provide). Next, copy the original configs for use by scanbd:

sudo cp -r /etc/sane.d /etc/scanbd/

Now edit /etc/scanbd/sane.d/dll.conf (the one under scanbd’s directory) to enable the actual backend for the Canon. For example, make sure it has canon_dr (or whichever backend supports the DR-F120) uncommented, and you can comment out “net” here (so that scanbd talks directly to USB) ￼. Essentially, the normal config and the scanbd config are inverses: normal uses only net, scanbd’s uses only the real driver.

4. Configure scanbd actions: Edit /etc/scanbd/scanbd.conf. Find the action scan { ... } block or add one if not present. Configure it to call a script on button press. For instance:

```
action scan {
   filter = "^scan.*" 
   numerical-trigger {
       from-value = 1
       to-value   = 0
   }
   desc = "Scan button pressed"
   script = "/etc/scanbd/scan.sh"
}
```

This assumes the DR-F120’s button event contains the word “scan”. (If unsure, we’ll do the test in a moment.) The numerical-trigger says we trigger when a certain option’s value goes from 1 to 0 – common for buttons (pressed/released). Now create the script /etc/scanbd/scan.sh:

```
#!/bin/bash
logger -t "scanbd: scan.sh" "Scan button pressed - triggering app"
curl -X POST http://localhost:5000/scan
```

This uses logger to log to syslog (for debugging) and then calls our app’s endpoint. We might include the --data or header if needed, but since our endpoint might not require any input, this is enough. Make it executable: chmod +x /etc/scanbd/scan.sh.

(Note: Using curl in a root-called script means we should ensure curl is installed: apt-get install curl. Alternatively, use wget or even Python if we had a small Python call. Curl is simplest.)

5. Test scanner button detection (optional): Before starting everything, it’s wise to test if scanbd sees the button. Start the scanbd service in debug/foreground:

```
sudo service scanbd stop   # ensure not already running
sudo scanbd -f -d5         # run in foreground with debug level 5
```

While this is running, press the scanner’s button. You should see output in the console indicating something was triggered. If the config is correct, it might say it’s running scan.sh. Also check syslog (tail -f /var/log/syslog) for the logger message “Scan button pressed - triggering app”. If you see that, the button press is being caught and our script called. If not, we may need to adjust the filter regex or trigger. For instance, if nothing happens, run scanimage -A in a separate terminal to see if any option changes when you press the button. The --all-options output will list all options including buttons ￼. Perhaps the option isn’t named “scan”. We might have to use a different pattern or a different trigger type (some use signal-trigger). Consult scanbd documentation or try the included sample configs:
In /etc/scanbd/scanner.d/, see if there’s a canon.conf or similar. If not, sometimes DR series might be similar to fujitsu or avision. The DR-F120 might internally use the avision backend? (Not sure, but if yes, the avision.conf might already have button definitions.) The ArchWiki snippet showed include(scanner.d/avision.conf) ￼. Check that file for clues. If it contains something like:

# for Canon DR scanners
device canon_dr:libusb:... {
   button "Scan" key = 1
   ...
}

(This is speculative; actual config may vary.) If we find specifics, use them. Otherwise, trial-and-error: set filter = ".*" and debug to see if anything triggers at all.

Once we get “button pressed” messages, stop scanbd for now (Ctrl+C if foreground).

6. Configure our Python application: Create the YAML config (say /home/pi/scan_app/config.yaml):

```
device: "net:localhost:canon_dr:libusb:001:002"   # using net:localhost because scanbd will manage the device
resolution: 300
mode: "Color"
source: "ADF"
format: "png"
api_url: "https://<your-server>/api/document/"
api_token: "<your bearer token here>"
temp_dir: "/tmp"
skip_blank: true
blank_threshold: 0.03    # 3% non-white = blank
log_level: "INFO"
log_file: "/home/pi/scan_app/scanner.log"
http_port: 5000
```

Adjust values as needed. Notably, we used the device with net:localhost:... prefix – this is to route scanning via scanbd. If you decide not to use scanbd (no button functionality), you could put the direct canon_dr:libusb:001:002. But we want the button, so we use the network path.

7. Start the Python application: Simply run it for now:

  python3 scan_app.py --config /home/pi/scan_app/config.yaml

(The app will be written to parse arguments for config path or use a default path). On startup, it should load config, configure logging (maybe print some info to console too). It may try a test scan or at least list the device. Check that it can see the scanner (if something’s wrong with device name, it might log an error). If all good, it will start the Flask server on port 5000 and then wait.

You should see a log like “Service started. Waiting for scan triggers…”.

8. Start scanbd: Now start the scanbd service in the background:

  sudo service scanbd start

This will begin polling the scanner for button events. (It will also effectively lock the scanner, but thanks to our net configuration, our app will still be able to request scans via the loopback saned mechanism.)

9. Test the end-to-end flow:
- Via Button: Load the logs (tail -f scanner.log) and then press the scanner’s Scan button. You should see entries appear: e.g. “Scan button pressed - triggering app” (from scanbd’s logger via syslog, maybe not in our app log yet, but in syslog) followed by our app logging “Received scan trigger (source=button)”, and then scanning steps: “Scanning started…”, “Scanned page 1…”, etc. The scanner should feed the pages through. If the feeder is empty and it switches to flatbed (if supported and configured), it might scan the flatbed or give an error. If an error occurs (like “sane_start: Invalid argument” or similar), check the SANE/scanimage output; we might need to adjust options.
Assuming success, once pages are done, the app should log blank page skipping results, then begin uploading. Look for an upload success log. On the server side (remote API), verify it received the files (if possible).
- Via HTTP: You can also test triggering from a network client. For example, from another computer (or the Pi itself), run:

curl -X POST http://<raspi-ip>:5000/scan

It should quickly return a response (like “started” message). Then check the logs to see the scanning proceeds just as with button. This confirms the HTTP control works. You can also try curl http://<raspi-ip>:5000/logs to see if the output includes the latest entries.

If everything is working, the workflow is: user puts documents in feeder, presses scanner button, then the pages get scanned and uploaded automatically – no further manual steps. :tada:

To stop the app, you’d Ctrl+C if running foreground. For production, we’d want to set it up as a systemd service so it auto-starts on boot and keeps running:

Example scan_service.service for systemd:

```
[Unit]
Description=Document Scanner Upload Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/scan_app
ExecStart=/usr/bin/python3 /home/pi/scan_app/scan_app.py --config config.yaml
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable it with sudo systemctl enable scan_service && sudo systemctl start scan_service. Also ensure scanbd.service is enabled.

Now both the hardware button and HTTP interface can be used in parallel. Scanbd ensures the button triggers do not conflict with ongoing scans by coordinating access ￼.

Testing and Calibration

We should perform various tests:
- Blank page skip tuning: Try scanning a completely blank sheet and confirm it’s skipped. Also try a very light content page (e.g. a paper with just a faint logo watermark) to ensure it’s not falsely skipped. If needed, adjust blank_threshold. The default 97% might be fine in most cases ￼, but this can be changed in config.
- Feeder vs Flatbed: If “Automatic” source is used, test scenarios: paper in feeder vs none in feeder (but something on flatbed). If flatbed scanning still doesn’t work on this model, note that to the user. It might be that flatbed simply errors out (due to the earlier SANE limitation). If that’s the case, our app could catch that error and inform “Flatbed not supported by driver” rather than hanging. Since the user expressed “ideally automatic input recognition”, we should clarify: On DR-F120 under Linux, automatic may effectively just mean using the ADF (since flatbed had issues). If new SANE versions fixed flatbed, then great – it will work.
- Multi-page and Last page: Ensure that after the last page, scanimage terminates. If not, consider using --batch-count or handle by user pressing cancel. Possibly the device does signal properly (most ADF scanners do, by returning SANE_STATUS_NO_DOCS or so).
- Error conditions: Try to simulate an error – e.g. no paper loaded and button pressed (should maybe do nothing or log a warning “No pages scanned” but still send an empty doc? Perhaps better to detect no pages and not POST anything). Or network API down (should log error and perhaps keep files).

Potential Enhancements and Options

The user mentioned being open to suggestions, so here are some additional features or alternatives that could be considered:
- Multi-Page PDF Generation: Instead of (or in addition to) sending individual image files, the application could compile all scanned images into a single PDF document. This could be done using a library like img2pdf in Python or calling Ghostscript/Imagemagick to convert images to PDF. This might be useful if the API or end system prefers a single PDF file. Since the requirement stated “image formats are sufficient”, we didn’t pursue PDF, but this is a simple extension.
- OCR Capability: If the ultimate goal is to have searchable documents, integrating OCR (Optical Character Recognition) could be beneficial. For instance, using Tesseract or an OCR API to extract text from scanned pages, then uploading the text or PDF+text to the server. This was not requested, but as a suggestion, this could add value for a future version.
- Multiple Button Actions: If the scanner had more buttons (e.g., one could imagine a “Scan to Email” button), the system could perform different actions based on which was pressed. For example, one button could trigger the normal upload as implemented, another could trigger a scan that emails the document to a preset address, etc. This would involve expanding the scanbd config for multiple actions and adding corresponding handlers in our app (or separate scripts). Our framework is already in place to trigger different code paths if we distinguish actions. We would need to read SCANBD_ACTION or pass a parameter from the script (like we did with a JSON payload in curl, e.g., {"action": "email"}) so the app knows which route to take.
- Web Interface: The current HTTP server is minimal (just endpoints). We could create a simple web page that allows the user to initiate a scan with a click and see the logs or status in the browser. Using Flask, we could serve an HTML template with an AJAX call to start scan and to refresh logs. This would make it more user-friendly (for someone who doesn’t want to SSH into Pi or use command line). Given time and scope, this might be a nice-to-have.
- Alternative to scanbd: If, for some reason, using scanbd is undesirable (it is a bit complex to configure), another approach is scanbuttond (an older project) or writing a custom USB listener. scanbuttond was mentioned but is largely unmaintained ￼. Some have written custom scripts for specific devices (there’s a GitHub project for Pixma button control ￼, but that’s device-specific). For DR-F120, scanbd is the robust solution. So we stick with that, but we note that it introduces complexity in SANE config.
- Daemon vs On-Demand: Our design is as a continuously running service. Another approach could be event-driven: for example, some systems trigger a udev event on button press (not common for scanners, more for multifunction printers where the scan button might register as a USB HID device). If that existed, we could capture it. But since none is documented for this scanner, the chosen route is fine.
- Logging to external systems: If desired, logs could be sent to an external log server or the remote API could accept log messages. Alternatively, integrating with systemd journal might suffice for the environment.
- Testing Mode: We’ve covered the test for button. We could also have a mode --test-scan that runs a single scan (maybe one page) to verify scanner connectivity and output (for initial setup debugging).
- Configuration GUI: Not likely needed, but an idea: use a web UI to edit the YAML config (so one doesn’t have to SSH and edit files). Possibly beyond scope.

Everything suggested above can be built on top of the current plan as needed, but the core system meets the requirements.

Source Citations

Throughout this plan, we referred to external documentation and examples to validate our approach:
- SANE scanimage manual confirms support for multiple image formats (PNM, TIFF, PNG, JPEG) and the usage of the --batch options for ADF scanning ￼ ￼. This is how we know we can produce multiple files until the feeder is empty ￼ ￼. It also notes that not all scanners signal an empty feeder, hence the --batch-count consideration ￼.
- The scanpdf project by Virantha demonstrates a similar concept (scanning to PDF, integrating with scanbd). It specifically highlights features like blank page removal and scanbd integration ￼ ￼. We took inspiration from its approach to blank pages, using a threshold for white space ￼, and its use of scanbd environment variables to trigger actions.
- The ArchWiki on Scanner Button Daemon (scanbd) was invaluable to understand how to configure and use scanbd. It explains the need for rerouting SANE to net and how scanbd locks and releases the device ￼ ￼. We referenced its example action script and config to know how to catch the “scan” action and use a script to respond ￼ ￼.
- A Unix StackExchange Q&A confirmed that using scanbd is the proper way to make scanner buttons work with SANE ￼, reinforcing our decision to use it.
- The Stack Overflow example on uploading multiple files via Python requests guided our construction of the files payload for the API upload ￼.
- Finally, forum posts on Raspberry Pi and others gave us insight into DR-F120 support on Linux. We learned that the device is recognized as canon_dr:libusb:... and some issues people faced (requiring perhaps newer backends) ￼ ￼. Also the SANE devices list snippet confirmed ADF is working for DR-F120 but flatbed might not ￼.

All these sources ensure that our implementation plan is grounded in known working practices and can be executed with available tools on a Raspberry Pi running Linux.

With this plan, the development can proceed with high confidence of fulfilling the user’s requirements. We have outlined the steps to implement and configure each part of the system, along with fallback strategies and testing procedures. The end result will be a flexible, configurable scanning service that automates the capture and delivery of documents, initiated either by the press of a physical button or through a network request, making the scanning workflow much more efficient.
