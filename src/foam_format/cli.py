from .core import format_body, is_not_formatable
from pathlib import Path
import os
import logging
import sys
from tqdm import tqdm
import click
import re


@click.command()
@click.option("--inline", help="Whether to directly include changes into file")
@click.option("--target", help="The target folder to recursively scan.")
@click.option("--skip_operator_ws", help="The person to greet.", is_flag=True)
@click.option(
    "--skip_ifdef_FULLDEBUG_indentation", help="The person to greet.", is_flag=True
)
def main(**kwargs):
    fn = Path(kwargs["target"])
    skip_if_orig_exists = False
    logging.basicConfig(format="[FOAM-FORMAT] %(message)s", level=20)
    if fn.is_dir():
        file_list = []
        logging.info("collecting files")
        for r, ds, fs in os.walk(fn):
            # dont descent into Make folders
            exclude = ["Make", "lnInclude"]
            ds[:] = [d for d in ds if d not in exclude]
            for f in fs:
                # NOTE currently header files are not formated
                if is_not_formatable(r, f):
                    continue
                # if ".orig" in f:
                #    continue
                # if skip_if_orig_exists and (Path(r) / f"{f}.orig").exists():
                #    continue
                file_list.append(Path(r) / f)
    else:
        file_list = [Path(fn)]

    logging.info(f"formating")
    lines = 0
    diffs = {}
    for f in tqdm(file_list):
        l, diff =  format_body(f, kwargs)
        diffs[f] = diff
        lines += l

    if lines != 0 and not kwargs.get("inline"):
        logging.warn(f"Reformating needed")
        for f, diff in diffs.items():
            for line in diff:
                match = re.search(":[0-9]*:", line)
                if match:
                    line_nr = match.group(0) 
                    print(f"::error file={f},line={line_nr}::Needs reformating")
        sys.exit(1)

    logging.info(f"reformated {lines} lines in {len(file_list)} files")
