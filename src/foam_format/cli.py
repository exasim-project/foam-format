from .core import format_body, is_not_formatable
from pathlib import Path
import os
import logging
import sys
from tqdm import tqdm


def main():
    fn = Path(sys.argv[1])
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
    for f in tqdm(file_list):
        lines += format_body(f)
    logging.info(f"reformated {lines} lines")
