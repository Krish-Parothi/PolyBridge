import sys
sys.path.insert(0, ".")
from tree_sitter import Language, Parser
import tree_sitter_verilog as tsverilog

lang = Language(tsverilog.language())
parser = Parser(lang)
tree = parser.parse("a = 32'd15;".encode("utf-8"))
def dump(n):
    print(n.type, repr(n.text.decode("utf-8")))
    for c in n.children: dump(c)
dump(tree.root_node)

