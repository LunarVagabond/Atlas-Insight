# C/C++ has no import-graph edges: #include produces file-level deps, not module
# graph edges, and would create excessive noise. Import graph analysis is skipped.
extract_edges = None
