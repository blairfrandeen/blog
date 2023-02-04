import sys, os

INTERP = f"{os.path.expanduser('~')}/datum-b.com/venv/bin/python3"
# INTERP is present twice so that the new Python interpreter knows the actual executable path
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

cwd = os.getcwd()
sys.path.append(cwd)
sys.path.append(cwd + "/projectname")  # You must add your project here

sys.path.insert(0, cwd + "/venv/bin")
sys.path.insert(0, cwd + "/venv/lib/python3.10.4/site-packages")
from app import app as application
