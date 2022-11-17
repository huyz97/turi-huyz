import networkx
import logging

from collections import defaultdict

from .statements import *
from .utils import walk_all_blocks
from .hierarchy import NoConcreteDispatch

logging.basicConfig()
log = logging.getLogger('CallGraph')
log.setLevel(logging.DEBUG)


class CallGraph:
    """
        Build call graph
    """

    def __init__(self, project):
        self.project = project
        self.graph = networkx.DiGraph()
        self._call_sites = defaultdict(lambda: defaultdict(list)) # caller -> callee
        self._callee_to_caller = defaultdict(lambda: defaultdict(list)) # callee -> caller
        self.build()

    def build(self):
        for block in walk_all_blocks(self.project.classes):
            method = self.project.blocks_to_methods[block]
            self.graph.add_node(method)
            for stmt in block.statements:
                if is_invoke(stmt):
                    self._add_invoke(method, block, stmt)

    def _add_invoke(self, container_m, block, invoke):
        if hasattr(invoke, 'invoke_expr'):
            invoke_expr = invoke.invoke_expr
        else:
            invoke_expr = invoke.right_op

        cls_name = invoke_expr.class_name
        method_name = invoke_expr.method_name
        method_params = invoke_expr.method_params

        if cls_name not in self.project.classes:
            # external classes are currently not supported
            return

        try:
            method = self.project.methods[(cls_name, method_name, method_params)]
        except KeyError as e:
            # TODO should we add a dummy node for "external" methods?
            log.warning('Cannot handle call to external method')
            return

        try:
            targets = self.project.hierarchy().resolve_invoke(invoke_expr, method, container_m)
        except NoConcreteDispatch as e:
            targets = []
            log.warning('2!!!!!!!!Could not resolve concrete dispatch. External method?')
        
        if targets==[]:
            targets = [method] # ensure the last node can be in the call_sites

        for target in targets:
            if target.class_name in self.project.classes:
                self.graph.add_node(target)
                self.graph.add_edge(container_m, target)
                self._call_sites[container_m][target].append(invoke_expr)
                # self._callee_to_caller[target][container_m].append(invoke_expr)

    def get_call_sites(self, method, target):
        return self._call_sites[method][target]

    def next(self, method):
        return self.graph.successors(method)

    def prev(self, method):
        return self.graph.predecessors(method)

    def get_call_chain(self, method, depth:int = 10):
        """
            method: address of the method object
            depth: function call depth,default is 10
            return: [chain1,chain2] in which chain1 = [method_leaf,method2,method3...]
        """
        if method not in self._callee_to_caller:
            return []
        # dfs
        stack = []
        stack.append([method])
        result_chain = []
        while (len(stack) > 0):
            chain = stack.pop()
            if chain[-1] not in self._callee_to_caller or len(chain) > depth: # now is the root node
                result_chain.append(chain)
                continue
            leaves_dict = self._callee_to_caller[chain[-1]]
            for leaf in leaves_dict:
                if leaf not in chain: # avoid loop
                    new_chain = chain.copy()
                    new_chain.append(leaf)
                    stack.append(new_chain)
        return result_chain

    def get_call_func_set(self, method, depth:int = 10):
        """
            method: address of the method object
            depth: function call depth,default is 10
            return: [chain1,chain2] in which chain1 = [method_leaf,method2,method3...]
        """
        if not self.graph.has_node(method):
            return set()
        # bfs
        queue = [method]
        func_set = set()
        layer = 0
        while queue != [] and layer <= depth:
            queue = list(set(queue))
            size = len(queue)
            layer += 1
            # print("-------------------------")
            # print(f"layer {layer}, nodes: {size}")
            while (size > 0):
                node = queue[0]
                del queue[0]
                size -= 1
                func_set.add(node)
                for prev_node in self.prev(node):
                    queue.append(prev_node)
        return func_set



