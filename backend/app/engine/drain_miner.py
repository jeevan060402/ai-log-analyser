import re
from typing import List, Dict, Optional, Tuple

class LogCluster:
    def __init__(self, cluster_id: int, log_template_tokens: List[str]):
        self.cluster_id = cluster_id
        self.log_template_tokens = log_template_tokens
        self.size = 1

    def get_template(self) -> str:
        return ' '.join(self.log_template_tokens)

class DrainNode:
    def __init__(self, depth: int = 1, digit_or_token: str = ''):
        self.depth = depth
        self.digit_or_token = digit_or_token
        self.child_nodes: Dict[str, 'DrainNode'] = {}
        self.cluster_list: List[LogCluster] = []

class DrainTemplateMiner:
    """
    High-speed, tree-based Drain log template miner.
    Clusters log messages into parameterized templates:
    e.g. 'Connection to 10.0.1.2:5432 timed out' -> 'Connection to <*> timed out'
    """
    def __init__(self, depth: int = 4, sim_th: float = 0.5, max_children: int = 100):
        self.depth = depth - 2
        self.sim_th = sim_th
        self.max_children = max_children
        self.root_node = DrainNode()
        self.clusters: Dict[int, LogCluster] = {}
        self.next_cluster_id = 1

    def match_or_create(self, content: str) -> Tuple[LogCluster, bool]:
        tokens = content.strip().split()
        if not tokens:
            tokens = ['<EMPTY>']

        log_len = str(len(tokens))
        curr_node = self.root_node
        
        if log_len not in curr_node.child_nodes:
            new_node = DrainNode(depth=1, digit_or_token=log_len)
            curr_node.child_nodes[log_len] = new_node
            curr_node = new_node
        else:
            curr_node = curr_node.child_nodes[log_len]

        curr_depth = 1
        for token in tokens:
            if curr_depth >= self.depth:
                break
            search_token = '<*>' if bool(re.search(r'\d', token)) else token
            if search_token in curr_node.child_nodes:
                curr_node = curr_node.child_nodes[search_token]
            elif '<*>' in curr_node.child_nodes:
                curr_node = curr_node.child_nodes['<*>']
            else:
                if len(curr_node.child_nodes) < self.max_children:
                    new_node = DrainNode(depth=curr_depth + 1, digit_or_token=search_token)
                    curr_node.child_nodes[search_token] = new_node
                    curr_node = new_node
                else:
                    if '<*>' not in curr_node.child_nodes:
                        new_node = DrainNode(depth=curr_depth + 1, digit_or_token='<*>')
                        curr_node.child_nodes['<*>'] = new_node
                        curr_node = new_node
                    else:
                        curr_node = curr_node.child_nodes['<*>']
            curr_depth += 1

        selected_cluster = None
        max_sim = -1.0
        for cluster in curr_node.cluster_list:
            sim, num_params = self._seq_distance(cluster.log_template_tokens, tokens)
            if sim > max_sim:
                max_sim = sim
                selected_cluster = cluster

        if max_sim >= self.sim_th and selected_cluster is not None:
            updated_tokens = []
            for t1, t2 in zip(selected_cluster.log_template_tokens, tokens):
                if t1 == t2:
                    updated_tokens.append(t1)
                else:
                    updated_tokens.append('<*>')
            selected_cluster.log_template_tokens = updated_tokens
            selected_cluster.size += 1
            return selected_cluster, False
        else:
            new_cluster = LogCluster(self.next_cluster_id, tokens)
            self.clusters[self.next_cluster_id] = new_cluster
            self.next_cluster_id += 1
            curr_node.cluster_list.append(new_cluster)
            return new_cluster, True

    def _seq_distance(self, seq1: List[str], seq2: List[str]) -> Tuple[float, int]:
        if len(seq1) != len(seq2):
            return 0.0, 0
        sim_tokens = 0
        num_params = 0
        for token1, token2 in zip(seq1, seq2):
            if token1 == '<*>':
                num_params += 1
                continue
            if token1 == token2:
                sim_tokens += 1
        return float(sim_tokens) / len(seq1), num_params
