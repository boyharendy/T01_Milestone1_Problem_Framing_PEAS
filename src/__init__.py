"""Package initialization untuk pemodelan graf dan algoritma penelusuran cerdas."""

try:
    from .graph_model import EvacuationGraph, Node, Edge, build_banda_aceh_graph
except ImportError:
    from src.graph_model import EvacuationGraph, Node, Edge, build_banda_aceh_graph
