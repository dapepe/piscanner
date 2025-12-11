# 1) Make sure venv support is installed
sudo apt update
sudo apt install python3-venv python3-full

# 2) Create and activate a virtual environment
cd /opt/piscan
python3 -m venv .venv
source .venv/bin/activate

# 3) Upgrade pip inside the venv and install requirements
pip install --upgrade pip
pip install -r requirements.txt

After that, always activate it before running your app:

cd /opt/piscan
source .venv/bin/activate
# run your script here, e.g.:
python main.py
