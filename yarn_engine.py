"""
yarn_engine.py
Lightweight Python Yarn Spinner Runtime for CHRONICLES OF DUNWICK: DEFYING FATE (1924)
Inspired by YarnSpinner (YarnSpinnerTool/YarnSpinner).

Supports:
- Node definitions (`title: ...`, `tags: ...`, `---`, `===`)
- Character speech lines (`Speaker: text`)
- Options / branching choices (`-> Text` with child response lines, conditions, jumps)
- Inline conditional blocks (`<<if ...>>`, `<<elseif ...>>`, `<<else>>`, `<<endif>>`)
- Variable assignment & arithmetic (`<<set $var = value>>`, `<<set $var += 1>>`)
- Node jumps (`<<jump NodeName>>`)
- Dynamic variable expansion (`{$var}` in text)
- Built-in functions in conditions: `visited("Node")`, `has_item("Key")`, `loop()`, `day()`, `trust()`, `suspicion()`
"""

import os
import re
from typing import Any, Callable


class YarnOption:
    def __init__(
        self,
        text: str,
        target_node: str | None = None,
        condition: str | None = None,
        response_lines: list[str] = None,
    ):
        self.text = text
        self.target_node = target_node
        self.condition = condition
        self.response_lines = response_lines or []


class YarnLine:
    def __init__(self, speaker: str | None, text: str, tags: list[str] = None):
        self.speaker = speaker
        self.text = text
        self.tags = tags or []


class YarnNode:
    def __init__(self, title: str, tags: list[str], content: list[str]):
        self.title = title.strip()
        self.tags = tags
        self.raw_lines = content


class YarnDialogueEngine:
    def __init__(self):
        self.nodes: dict[str, YarnNode] = {}
        self.variables: dict[str, Any] = {
            "loop_id": 1,
            "current_day": 1,
            "player_id": "arthur",
            "player_name": "Lord Arthur",
            "scenario": "SELF_DEATH",
            "credibility": 80,
            "held_item": "",
            "threat_foiled": False,
            "threat_deduced": False,
        }
        self.visited_nodes: set[str] = set()
        self.custom_command_handlers: dict[str, Callable[[list[str]], None]] = {}

        # Runtime active state
        self.current_node: YarnNode | None = None
        self.program_counter: int = 0
        self.is_waiting_for_choice: bool = False
        self.current_options: list[YarnOption] = []
        self.current_line: YarnLine | None = None
        self.is_finished: bool = True

        # Queue of response lines from chosen option
        self.execution_queue: list[str] = []

    def register_command(self, cmd_name: str, handler: Callable[[list[str]], None]):
        self.custom_command_handlers[cmd_name] = handler

    def set_variable(self, name: str, value: Any):
        clean_name = name.lstrip("$")
        self.variables[clean_name] = value

    def get_variable(self, name: str, default: Any = None) -> Any:
        clean_name = name.lstrip("$")
        return self.variables.get(clean_name, default)

    def load_yarn_string(self, yarn_text: str):
        """Parses Yarn Spinner syntax text into nodes."""
        raw_nodes = yarn_text.split("===")
        for chunk in raw_nodes:
            chunk = chunk.strip()
            if not chunk:
                continue

            parts = chunk.split("---", 1)
            header_part = parts[0]
            body_part = parts[1] if len(parts) > 1 else ""

            title = ""
            tags = []
            for hline in header_part.splitlines():
                hline = hline.strip()
                if hline.startswith("title:"):
                    title = hline.split(":", 1)[1].strip()
                elif hline.startswith("tags:"):
                    tags = [t.strip() for t in hline.split(":", 1)[1].split() if t.strip()]

            if title:
                lines = [l for l in body_part.splitlines()]
                self.nodes[title] = YarnNode(title, tags, lines)

    def load_yarn_file(self, file_path: str):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Yarn file not found: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            self.load_yarn_string(f.read())

    def start_dialogue(self, node_title: str) -> bool:
        if node_title not in self.nodes:
            return False

        self.current_node = self.nodes[node_title]
        self.visited_nodes.add(node_title)
        self.program_counter = 0
        self.is_waiting_for_choice = False
        self.current_options = []
        self.current_line = None
        self.execution_queue = []
        self.is_finished = False
        self.advance()
        return True

    def _eval_condition(self, expr_str: str) -> bool:
        expr = expr_str.strip()
        if not expr:
            return True

        def var_replacer(match):
            var_name = match.group(1)
            val = self.variables.get(var_name, None)
            return repr(val)

        subbed = re.sub(r"\$([a-zA-Z0-9_]+)", var_replacer, expr)

        eval_env = {
            "visited": lambda node_name: node_name in self.visited_nodes,
            "has_item": lambda item_name: self.variables.get("held_item") == item_name,
            "loop": lambda: self.variables.get("loop_id", 1),
            "day": lambda: self.variables.get("current_day", 1),
            "credibility": lambda: self.variables.get("credibility", 80),
            "true": True,
            "false": False,
            "null": None,
        }

        try:
            res = eval(subbed, {"__builtins__": {}}, eval_env)
            return bool(res)
        except Exception:
            return False

    def _interpolate(self, text: str) -> str:
        def repl(match):
            key = match.group(1).lstrip("$")
            return str(self.variables.get(key, ""))

        return re.sub(r"\{\$?([a-zA-Z0-9_]+)\}", repl, text)

    def advance(self):
        """Advances execution until the next dialogue line or choice options."""
        if self.is_finished:
            return

        # 1. Process any pending lines queued from a chosen option response
        while self.execution_queue:
            raw_line = self.execution_queue.pop(0)
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("<<set "):
                stmt = line[6:].rstrip(">").strip()
                self._execute_set_statement(stmt)
                continue
            if line.startswith("<<jump "):
                target = line[7:].rstrip(">").strip()
                if target in self.nodes:
                    self.start_dialogue(target)
                return
            if line.startswith("<<") and line.endswith(">>"):
                cmd_content = line[2:-2].strip()
                cmd_parts = cmd_content.split()
                if cmd_parts and cmd_parts[0] in self.custom_command_handlers:
                    self.custom_command_handlers[cmd_parts[0]](cmd_parts[1:])
                continue

            # It's a speech line from the response
            speaker = None
            text = line
            tags = []
            if "#" in text:
                parts = text.split("#")
                text = parts[0].strip()
                tags = [p.strip() for p in parts[1:]]

            if ":" in text and not text.startswith("http"):
                spk, body = text.split(":", 1)
                speaker = spk.strip()
                text = body.strip()

            self.current_line = YarnLine(speaker, self._interpolate(text), tags)
            self.is_waiting_for_choice = False
            return

        if self.current_node is None:
            self.is_finished = True
            return

        lines = self.current_node.raw_lines
        n_lines = len(lines)
        if_stack = []

        while self.program_counter < n_lines:
            raw_line = lines[self.program_counter]
            self.program_counter += 1
            line = raw_line.strip()

            if not line:
                continue

            is_active = all(if_stack) if if_stack else True

            # Handle conditional control structures
            if line.startswith("<<if "):
                cond_text = line[5:].rstrip(">").strip()
                res = self._eval_condition(cond_text) if is_active else False
                if_stack.append(res)
                continue
            elif line.startswith("<<elseif ") or line.startswith("<<else if "):
                cond_text = line.split("if", 1)[1].rstrip(">").strip()
                if len(if_stack) > 0:
                    prev = if_stack.pop()
                    parent_active = all(if_stack) if if_stack else True
                    if parent_active and not prev:
                        res = self._eval_condition(cond_text)
                    else:
                        res = False
                    if_stack.append(res)
                continue
            elif line == "<<else>>":
                if len(if_stack) > 0:
                    prev = if_stack.pop()
                    parent_active = all(if_stack) if if_stack else True
                    if_stack.append(parent_active and not prev)
                continue
            elif line == "<<endif>>" or line == "<</if>>":
                if if_stack:
                    if_stack.pop()
                continue

            if not is_active:
                continue

            # Command: <<jump Node>>
            if line.startswith("<<jump "):
                target = line[7:].rstrip(">").strip()
                if target in self.nodes:
                    self.current_node = self.nodes[target]
                    self.visited_nodes.add(target)
                    self.program_counter = 0
                    lines = self.current_node.raw_lines
                    n_lines = len(lines)
                    continue
                else:
                    self.is_finished = True
                    return

            # Command: <<set $var = val>>
            if line.startswith("<<set "):
                stmt = line[6:].rstrip(">").strip()
                self._execute_set_statement(stmt)
                continue

            # Custom commands
            if line.startswith("<<") and line.endswith(">>"):
                cmd_content = line[2:-2].strip()
                cmd_parts = cmd_content.split()
                if cmd_parts and cmd_parts[0] in self.custom_command_handlers:
                    self.custom_command_handlers[cmd_parts[0]](cmd_parts[1:])
                continue

            # Option block detected: -> or [[
            if line.startswith("->") or (line.startswith("[[") and not line.endswith(":")):
                options_list = self._gather_option_block(lines, self.program_counter - 1, if_stack)
                if options_list:
                    self.current_options = options_list
                    self.is_waiting_for_choice = True
                    return
                continue

            # Dialogue Line
            speaker = None
            text = line
            tags = []
            if "#" in text:
                parts = text.split("#")
                text = parts[0].strip()
                tags = [p.strip() for p in parts[1:]]

            if ":" in text and not text.startswith("http"):
                spk, body = text.split(":", 1)
                speaker = spk.strip()
                text = body.strip()

            self.current_line = YarnLine(speaker, self._interpolate(text), tags)
            self.is_waiting_for_choice = False
            return

        self.is_finished = True
        self.current_line = None

    def _gather_option_block(self, lines: list[str], start_idx: int, if_stack: list[bool]) -> list[YarnOption]:
        """Collects all sibling options and their respective indented child response blocks."""
        options: list[YarnOption] = []
        n_lines = len(lines)
        idx = start_idx

        current_opt: YarnOption | None = None

        while idx < n_lines:
            rline = lines[idx]
            sline = rline.strip()

            if not sline:
                idx += 1
                continue

            # Check if this line is an option marker
            if sline.startswith("->"):
                opt_str = sline[2:].strip()
                opt_cond = None
                if "<<if " in opt_str:
                    text_part, cond_part = opt_str.split("<<if ", 1)
                    opt_str = text_part.strip()
                    opt_cond = cond_part.rstrip(">").strip()

                target_node = None
                if "|" in opt_str:
                    text_part, target_node = opt_str.split("|", 1)
                    opt_str = text_part.strip()
                    target_node = target_node.strip()

                # Only include option if its condition evaluates to True
                if opt_cond is None or self._eval_condition(opt_cond):
                    interp_text = self._interpolate(opt_str.strip('"'))
                    current_opt = YarnOption(interp_text, target_node, opt_cond)
                    options.append(current_opt)
                else:
                    current_opt = None
                idx += 1
            elif sline.startswith("[[") and sline.endswith("]]"):
                inner = sline[2:-2].strip()
                target_node = None
                opt_txt = inner
                if "|" in inner:
                    opt_txt, target_node = inner.split("|", 1)
                current_opt = YarnOption(self._interpolate(opt_txt.strip()), target_node.strip())
                options.append(current_opt)
                idx += 1
            else:
                # This line is inside an option's response block
                # Check indentation or if it belongs to current_opt
                if current_opt is not None and (rline.startswith("    ") or rline.startswith("\t")):
                    current_opt.response_lines.append(sline)
                    idx += 1
                elif sline.startswith("<<endif>>") or sline == "===":
                    break
                else:
                    # Non-indented regular line means the option group ended
                    break

        self.program_counter = idx
        return options

    def select_option(self, option_index: int) -> bool:
        if not self.is_waiting_for_choice or option_index < 0 or option_index >= len(self.current_options):
            return False

        chosen = self.current_options[option_index]
        self.is_waiting_for_choice = False
        self.current_options = []

        if chosen.target_node and chosen.target_node in self.nodes:
            self.start_dialogue(chosen.target_node)
            return True
        elif chosen.response_lines:
            self.execution_queue = list(chosen.response_lines)
            # Pre-evaluate any <<set >> statements in this response block so variables are instantly accessible
            for r in chosen.response_lines:
                rs = r.strip()
                if rs.startswith("<<set "):
                    self._execute_set_statement(rs[6:].rstrip(">").strip())
            self.advance()
            return True
        else:
            self.advance()
            return True

    def _execute_set_statement(self, stmt: str):
        try:
            if "+=" in stmt:
                var, val_str = stmt.split("+=", 1)
                var = var.strip().lstrip("$")
                curr = self.variables.get(var, 0)
                add_val = eval(val_str.strip(), {"__builtins__": {}}, {})
                self.variables[var] = curr + add_val
            elif "-=" in stmt:
                var, val_str = stmt.split("-=", 1)
                var = var.strip().lstrip("$")
                curr = self.variables.get(var, 0)
                sub_val = eval(val_str.strip(), {"__builtins__": {}}, {})
                self.variables[var] = curr - sub_val
            elif "=" in stmt or "to" in stmt:
                splitter = "=" if "=" in stmt else "to"
                var, val_str = stmt.split(splitter, 1)
                var = var.strip().lstrip("$")
                val_clean = val_str.strip()
                if val_clean.lower() == "true":
                    self.variables[var] = True
                elif val_clean.lower() == "false":
                    self.variables[var] = False
                else:
                    self.variables[var] = eval(val_clean, {"__builtins__": {}}, {})
        except Exception:
            pass
