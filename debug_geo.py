import sys, json, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from geometry import classify_walls, build_wall_graph, detect_junctions

# Test Plan A partitions
with open('backend/fallback/plan_a_coords.json') as f:
    data_a = json.load(f)

classified = classify_walls(data_a)
partitions = [c for c in classified if c['type'] == 'partition']
print(f"Plan A - partitions: {len(partitions)}")
for c in classified:
    print(f"  {c['wall_id']}: {c['type']}")

print()

# Test Plan B T-junctions
with open('backend/fallback/plan_b_coords.json') as f:
    data_b = json.load(f)

G = build_wall_graph(data_b)
j = detect_junctions(G)
print(f"Plan B - T-junctions: {len(j['T_junctions'])}")
print(f"Plan B - L-corners: {len(j['L_corners'])}")
print(f"Plan B - Endpoints: {len(j['endpoints'])}")
print(f"Plan B - Crossroads: {len(j['crossroads'])}")
for node in G.nodes():
    print(f"  Node {node}: degree {G.degree(node)}")
