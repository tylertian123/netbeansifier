import sys
import os
import re
import shutil
import tempfile
from distutils import dir_util
from typing import Any, List
import pathspec

pattern = re.compile(r"#\[(\w+)\]#")

HELP = """
Usage: python3 netbeansify.py <input directory> [options]

Available Options:
    --help
    --name      <project name>
    --mainclass <main class incl. package>
    --out       <output dir> (optional if using --zip)
    --template  <template dir>
    --sourcever <source compat. java version>
    --targetver <target compat. java version>
    --jvmargs   <additional jvm args>
    --javacargs <additional javac args>
    --zip

netbeansifier supports gitignore-style ignore files.
Files named .nbignore contain patterns for files/directories that are excluded during copying.
The file itself is also ignored.
""".strip()

args = {
    "project_name": None,
    "javac_source": "11",
    "javac_target": "11",
    "main_class": None,
    "#out": None,
    "#template": os.path.join(os.path.dirname(__file__), "template/"),
}

long_opts = {
    "name": "project_name",
    "sourcever": "javac_source",
    "targetver": "javac_target",
    "mainclass": "main_class",
    "jvmargs": "jvm_args",
    "javacargs": "javac_args",
    "out": "#out",
    "template": "#template",
}

makezip = False
source_path = None
it = iter(sys.argv)
for s in it:
    if s.startswith("--"):
        if s == "--help":
            print(HELP)
            sys.exit(0)
        if s == "--zip":
            makezip = True
        else:
            try:
                opt = long_opts[s[2:]]
                args[opt] = next(it)
            except KeyError:
                print("Invalid option:", s, file=sys.stderr)
                sys.exit(1)
            except StopIteration:
                print("Option", s, "needs a value", file=sys.stderr)
                sys.exit(1)
    else:
        source_path = s

if source_path is None or not os.path.isdir(source_path):
    print("Source path not provided", file=sys.stderr)
    sys.exit(1)

if args["#out"] is None and not makezip:
    print("Destination path not provided", file=sys.stderr)
    sys.exit(1)

# Default values
args["project_name"] = args["project_name"] or os.path.basename(source_path)
args["main_class"] = args["main_class"] or args["project_name"]

def netbeansify():
    # Copy over the template
    dir_util.copy_tree(args["#template"], args["#out"])

    for dirpath, _, files in os.walk(args["#out"]):
        for file in files:
            file = os.path.join(dirpath, file)
            print("Generating", file)
            try:
                with open(file, "r") as f:
                    text = f.read()
                with open(file, "w") as f:
                    f.write(pattern.sub(lambda match: args.get(match.group(1), ""), text))
            except UnicodeDecodeError:
                print("File", file, "is a binary, skipping...")

    # Copy over the files
    def copy_dir(src_dir: str, dest_dir: str, ignores: List[Any]):
        ignore_file = os.path.join(src_dir, ".nbignore")
        has_ignore = False
        if os.path.exists(ignore_file):
            with open(ignore_file, "r") as f:
                ignores.append(pathspec.PathSpec.from_lines("gitwildmatch", f))
            has_ignore = True
        with os.scandir(src_dir) as sdit:
            for entry in sdit:
                if entry.name == ".nbignore" or any(spec.match_file(entry.path) for spec in ignores):
                    continue
                if entry.is_file():
                    # copy the file over
                    shutil.copyfile(os.path.join(src_dir, entry.name), os.path.join(dest_dir, entry.name))
                elif entry.is_dir():
                    copy_dir(os.path.join(src_dir, entry.name), os.path.join(dest_dir, entry.name), ignores)
        if has_ignore:
            ignores.pop()

    copy_dir(source_path, os.path.join(args["#out"], "src/"), [])
    try:
        shutil.copy(os.path.join(os.path.dirname(__file__), "netbeanz.png"), args["#out"])
    except OSError:
        print("Warning: Logo not found! This is very important!", file=sys.stderr)

if args["#out"] is None:
    with tempfile.TemporaryDirectory() as tempdir:
        out_path = os.path.join(tempdir, args["project_name"])
        args["#out"] = out_path
        netbeansify()
        shutil.make_archive(args["project_name"], "zip", tempdir, args["project_name"])
else:
    netbeansify()
    if makezip:
        print("Making zip file...")
        shutil.make_archive(args["project_name"], "zip", os.path.dirname(os.path.abspath(args["#out"])), os.path.basename(args["#out"]))



print("Done.")
