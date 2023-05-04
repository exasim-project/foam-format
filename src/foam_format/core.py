from subprocess import check_output, CalledProcessError
import sys
import re
import os
from pathlib import Path
from shutil import copy
import pkg_resources

from collections import defaultdict


def _apply_rule(
    in_: list[str],
    predicate,
    reformat,
    ignore=lambda x: x.lstrip().startswith("//"),
) -> list[str]:
    out = []
    for line in in_:
        if ignore(line):
            out.append(line)
            continue
        if predicate(line):
            reformat(out, line)
        else:
            out.append(line)
    return out


def remove_ws_from_operators(in_str: list[str]) -> list[str]:
    def f(out, line):
        for op in [" / ", " * "]:
            line = line.replace(op, op.replace(" ", ""))
        out.append(line)

    return _apply_rule(
        in_str, predicate=lambda x: re.findall("[ ][/*][ ]", x), reformat=f
    )


def remove_ws_from_loop_header(in_str: list[str]) -> list[str]:
    def f(out, line):
        line = line.replace(f" {op} ", op)

    return _apply_rule(
        in_str,
        predicate=lambda x: re.findall("[=<]", x),
        reformat=f,
        ignore=lambda x: not "for (" in line,
    )


def fix_indent_comment_or(in_str: list[str]) -> list[str]:
    out = []
    for line in in_str:
        line_striped = line.lstrip()
        lw = len(line) - len(line.lstrip())
        if (
            line_striped.startswith("&&")
            or line_striped.startswith("||")
            or line_striped.startswith("==")
        ) and lw > 0:
            out.append(line[3:])
        else:
            out.append(line)
    return out


def add_newline_to_func_before_colon(in_str: list[str]) -> list[str]:
    class F:
        # TODO colon can be also after public and private in which case it should be ignored
        def __init__(self):
            self.state = False
            self.colon = False

        def __call__(self, out, line):
            if not line:
                return
            if not self.colon:
                ws = len(line) - len(line.lstrip())
                out.append(" " * (ws - 4) + ":")
                out.append(line.replace(" : ", " "))
                # Prepare for list of more members to indent
                if line.endswith(","):
                    self.state = True
                    self.colon = True
                else:
                    self.state = False
                    self.colon = False
                return

            # append ws as long as line is terminated by a comma
            if line.endswith(","):
                out.append(line[2:])
            else:
                out.append(line[2:])
                self.state = False
                self.colon = False

        @property
        def predicate(self):
            def predicate_impl(x):
                if self.state:
                    return lambda x: True
                if len(x) == 0:
                    return False
                if x.lstrip()[0] == ":":
                    self.state = True
                    return True

            return predicate_impl

    f = F()

    return _apply_rule(
        in_str,
        predicate=f.predicate,
        reformat=f,
    )


def fix_stream_alignment(in_str: list[str]) -> list[str]:
    class F:
        # TODO does not work with >>

        insert = 0
        keep = ""

        def __call__(self, out, line):
            # find out if there is anything before first <<
            cont = line.lstrip().startswith("<<")

            # check if there is an endl to keep
            if line.lstrip() == "<< endl":
                self.keep += "<< endl "
                return

            if not cont:
                stream_var = line.split("<<")[0].lstrip()
                # get number of ws to add
                self.insert = 4 - len(stream_var)
                # get if negative check if there is some ws to take away
                if self.insert < 0 and self.insert > -2:
                    line = line.replace(stream_var, stream_var[: self.insert])
                if self.insert > 0:
                    line = line.replace(stream_var, stream_var + " " * self.insert)
            else:
                # check if we need to add something from the keep pile
                if self.insert > 0:
                    ws = len(line) - len(line.lstrip())
                    line = " " * (self.insert + ws) + self.keep + line.lstrip()
                    self.keep = ""
                if self.insert < 0 and self.insert > -2:
                    ws = len(line) - len(line.lstrip()) + self.insert
                    line = " " * ws + self.keep + line.lstrip()
                    self.keep = ""

            out.append(line)

    return _apply_rule(in_str, predicate=lambda x: re.findall("<<", x), reformat=F())


def fix_indentation_of_ifdef(in_str: list[str]) -> list[str]:
    """ """
    out = []
    found = False
    ws = 0
    for i, line in enumerate(in_str):
        # TODO find closing endif
        if line.startswith("#ifdef FULLDEBUG"):
            found = True
            ws = len(in_str[i + 1]) - len(in_str[i + 1].lstrip())
            out.append(" " * ws + line)
            continue
        elif found and line.startswith("#endif"):
            out.append(" " * ws + line)
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
    def f(out, line):
        out.append(" " * 4 + line)

    return _apply_rule(
        in_str,
        predicate=lambda x: x.startswith("make") or x.startswith("define"),
        reformat=f,
    )


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


def format_body(fn, kwargs):
    clang_format_path = pkg_resources.resource_filename(
        "foam_format", "clang_format.body"
    )
    fn_orig = str(fn) + ".orig"
    copy(fn, fn_orig)
    try:
        post_clang_format = check_output(
            ["clang-format", "-Werror", "-style", f"file:{clang_format_path}", fn]
        ).decode("utf-8")
    except:
        print("failed on", fn)
    body_str = "".join(post_clang_format)
    body_str = body_str.split("\n")
    header, body = separate_header(body_str)
    body = add_newline_to_func_before_parenthesis(body)
    body = add_newline_to_func_before_colon(body)
    # body = remove_ws_from_loop_header(body)
    if not kwargs.get("skip_operator_ws"):
        body = remove_ws_from_operators(body)
    if not kwargs.get("skip_ifdef_FULLDEBUG_indentation"):
        body = fix_indentation_of_ifdef(body)
    body = fix_stream_alignment(body)
    body = fix_indent_comment_or(body)
    body = indent_namespace(body)
    # body = indent_namespace(body)
    with open(fn, "w") as fh:
        fh.write("\n".join(header))
        fh.write("\n".join(body))

    try:
        check_output(["diff", "-y", "--suppress-common-lines", fn_orig, fn])
        diff = []
    except CalledProcessError as e:
        diff = "".join(e.output.decode("utf-8")).split("\n")

    os.remove(fn_orig)

    return len(diff)


def is_not_formatable(r, fn):
    # if the file name is same as folder name it is a header file
    if fn.endswith(".C"):
        return False
    if fn.endswith("gz"):
        return True
    # All header files end with .H except the I.H files
    if fn.endswith(".H"):
        if fn.endswith("I.H"):
            return False
        else:
            return True
    return True
