from subprocess import check_output
import sys
import re
import os
from pathlib import Path
from shutil import copy


def remove_ws_from_operators(in_str: list[str]) -> list[str]:
    out = []
    for line in in_str:
        if line.startswith("//"):
            out.append(line)
            continue
        for op in ["+", "-", "/", "*"]:
            line = line.replace(f" {op} ", op)
        out.append(line)
    return out


def add_newline_to_func_before_colon(in_str: list[str]) -> list[str]:
    out = []
    for line in in_str:
        if re.findall(" : ", line):
            out.append(":")
            out.append(line.replace(" : ", "   "))
        else:
            out.append(line)
    return out


def remove_ws_from_loop_header(in_str: list[str]) -> list[str]:
    out = []
    for line in in_str:
        if not "for (" in line:
            out.append(line)
            continue
        for op in ["=", "<"]:
            line = line.replace(f" {op} ", op)
        out.append(line)
    return out


def fix_os_stream_alignment(in_str: list[str]) -> list[str]:
    # TODO keep two endl on one line
    out = []
    os_state = False
    for line in in_str:
        if "os <<" in line:
            line = line.replace(f"os <<", "os  <<")
            os_state = "started"
            out.append(line)
        elif os_state and not ";" in line:
            out.append(" " + line)
        elif os_state and ";" in line:
            os_state = False
            out.append(" " + line)
        else:
            out.append(line)
    return out


def fix_indent_comment_or(in_str: list[str]) -> list[str]:
    out = []
    for line in in_str:
        line_striped = line.lstrip()
        lw = len(line) - len(line.lstrip())
        if (line_striped.startswith("&&") or line_striped.startswith("||")) and lw > 0:
            out.append(line[3:])
        else:
            out.append(line)
    return out


def fix_info_stream_alignment(in_str: list[str]) -> list[str]:
    out = []
    os_state = False
    for line in in_str:
        if "Info <<" in line:
            line = line.replace(f"Info <<", "Info<<")
            os_state = "started"
            out.append(line)
        elif os_state and not ";" in line:
            out.append(line[1:])
        elif os_state and ";" in line:
            os_state = False
            out.append(line[1:])
        else:
            out.append(line)
    return out


def fix_stream_alignment(in_str: list[str]) -> list[str]:
    out = []
    os_state = False
    for line in in_str:
        if ") <<" in line:
            line = line.replace(f") <<", ")   <<")
            os_state = "started"
            out.append(line)
        elif os_state and not ";" in line:
            out.append("  " + line)
        elif os_state and ";" in line:
            os_state = False
            out.append("  " + line)
        else:
            out.append(line)
    return out


def add_newline_to_func_before_parenthesis(in_str: list[str]) -> list[str]:
    """ """
    out = []
    for line in in_str:
        if line.endswith("("):
            lw = len(line) - len(line.lstrip())
            out.append(line[:-1].rstrip())
            out.append(" " * lw + "(")
        else:
            out.append(line)
    return out


def indent_namespace(in_str: list[str]) -> list[str]:
    out = []
    state = False
    for line in in_str:
        if line.startswith("namespace Foam"):
            state = True
            out.append(line)
        elif line.startswith("{") and state:
            out.append(line)
        elif not line.startswith("{") and state:
            out.append(" " * 4 + line)
        elif not line.startswith("}") and state:
            state = False
            out.append(line)
        else:
            out.append(line)
    return out


def separate_header(in_str: list[str]) -> tuple[list[str]]:
    header_end = "\*---------------------------------------------------------------------------*/"
    header = []
    body = []
    header_end_found = False
    for line in in_str:
        if header_end_found:
            body.append(line)
        else:
            header.append(line)
        if header_end in line:
            header.append("")
            header_end_found = True
    return header, body


def format_body(fn):
    print(f"formating {fn}")
    # copy(fn, str(fn) + ".orig")
    post_clang_format = check_output(
        ["clang-format", "-Werror", "-style", "file", fn]
    ).decode("utf-8")
    body_str = "".join(post_clang_format)
    body_str = body_str.split("\n")
    header, body = separate_header(body_str)
    body = add_newline_to_func_before_parenthesis(body)
    body = add_newline_to_func_before_colon(body)
    # body = remove_ws_from_loop_header(body)
    body = remove_ws_from_operators(body)
    body = fix_stream_alignment(body)
    body = fix_os_stream_alignment(body)
    body = fix_info_stream_alignment(body)
    body = fix_indent_comment_or(body)
    # body = indent_namespace(body)
    with open(fn, "w") as fh:
        fh.write("\n".join(header))
        fh.write("\n".join(body))


def is_header_file(r, fn):
    # if the file name is same as folder name it is a header file
    if fn.endswith(".C"):
        return False
    # All header files end with .H except the I.H files
    if fn.endswith(".H"):
        if fn.endswith("I.H"):
            return False
        else:
            return True


def main(fn):
    skip_if_orig_exists = False
    if fn.is_dir():
        for r, ds, fs in os.walk(fn):
            # dont descent into Make folders
            exclude = ["Make", "lnInclude"]
            ds[:] = [d for d in ds if d not in exclude]
            for f in fs:
                if is_header_file(r, f):
                    continue
                # if ".orig" in f:
                #    continue
                # if skip_if_orig_exists and (Path(r) / f"{f}.orig").exists():
                #    continue
                format_body(Path(r) / f)
    else:
        format_body(fn)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
