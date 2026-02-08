# Section 4: AERIS Protocol Design

---

<!-- Source: AERIS_Complete_For_Overleaf.tex, lines 319-380 -->
<!-- Extracted: 2026-02-07 -->
<!-- Sync rule: This file is the authoritative Section 4 source. Any edits should be made here first, then synced to the main .tex if needed. -->

## 4. AERIS Protocol Design

AERIS employs a three-layer hierarchical architecture.

### 4.1 Layer 1: Context-Adaptive Switching (CAS)

CAS selects the optimal transmission mode based on six features:
residual energy, link quality, distance to CH, cluster size, node density,
and fairness index.

Three modes are available:

- **Direct**: Single-hop to CH (low energy, short range)
- **Chain**: Multi-hop chain (energy-efficient, longer path)
- **Two-Hop**: Via relay node (balanced)

### 4.2 Layer 2: Skeleton Backbone

The skeleton backbone provides stable routing paths using PCA-based
principal axis analysis:

1. Compute principal axis of node positions
2. Select skeleton nodes along the axis
3. Form tree structure with O(log k) depth

### 4.3 Layer 3: Gateway Coordination

Gateway nodes reinforce critical paths between cluster heads and the
base station. Selection criteria:

```
Score_i = alpha * E_i + beta * C_i + gamma * L_i
```

where E_i is residual energy, C_i is centrality, and L_i is link
quality. A load limit prevents gateway overloading.

**Note**: Ablation analysis shows Gateway provides statistically significant PDR gains in 3/4 tested environments (see Section 6).

### 4.4 Algorithm Pseudocode

```
Algorithm: AERIS Gateway Selection
Input:  Nodes N, Base station BS, Gateway count k
Output: Selected gateways G

1. For each node n in N:
     score[n] = alpha * E_n + beta * C_n + gamma * L_n
2. G = TopK(score, k)
3. Apply load limit to G
4. Return G
```
