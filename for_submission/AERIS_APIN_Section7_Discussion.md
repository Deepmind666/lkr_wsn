# Section 7: Discussion

---

## 7. Discussion

This section interprets the publication results and highlights limitations.

### 7.1 Multi-Environment Performance

AERIS achieves the highest PDR in all four environments. The advantage is
largest in outdoor_suburban and indoor_factory, where absolute PDR is lower
for all protocols. This suggests AERIS is relatively more robust under harsh
channel conditions, even though absolute delivery ratios drop substantially
in outdoor_urban and indoor_factory scenarios.

### 7.2 Gateway Negative Effect (Cross-Environment)

The ablation results show a consistent negative effect from the Gateway
module: disabling it improves PDR by +2% to +18% depending on environment.
This implies Gateway overhead (coordination + traffic concentration) can
outweigh its benefits under the current configuration. This is a key
limitation and should be explicitly stated in the paper.

### 7.3 CAS Tradeoff

CAS multi-mode is now triggerable, but higher CHAIN activation correlates
with lower PDR in sparse environments. This indicates a tradeoff between
diversifying routing modes and maintaining delivery reliability. TWO_HOP
remains very rare (<0.2%) even under aggressive settings, suggesting more
work is needed to make it practically useful.

### 7.4 Limitations

1) Results are from a Python simulator; NS-3 alignment is trend-level only.  
2) Experiments are limited to uniform random deployments and fixed packet size.  
3) Energy and latency tradeoffs are not fully characterized in the current
   publication evidence set.  

### 7.5 Future Work

1) Analyze the root cause of Gateway negative effect and redesign its
   selection or load-balancing strategy.  
2) Improve CAS to raise TWO_HOP usage without large PDR penalties.  
3) Run NS-3 parameter-aligned experiments to provide numeric validation.  
4) Extend tests to additional deployment patterns (corridor, hotspot).  

