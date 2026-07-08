# Employee Photo Automation Flow

This automated pipeline listens for image updates, moves files into cloud storage, and extracts face recognition telemetry.

## Structure
* `photos/` - Place new employee photos here.
* `upload_and_detect.py` - Core execution backend script.
* `result.json` - Generated facial intelligence analysis output file.

## Quick Trigger
Simply drop an image file into the `photos/` directory, commit the file, and push it to the remote branch. The pipeline completes the execution automatically.